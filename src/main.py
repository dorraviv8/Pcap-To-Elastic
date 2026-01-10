import os
import time

from prometheus_client import start_http_server

from pcap_reader import iter_packets, packet_to_document
from metrics import (
    pcap_packets_total,
    pcap_bytes_total,
    pcap_elastic_write_total,
    normalize_protocol,
)
from elastic_writer import create_es_client, get_index_name, write_document


def _read_max_packets() -> int | None:
    """
    Reads MAX_PACKETS from environment.

    Returns:
        int: maximum packets to process
        None: no limit (process full PCAP)
    """
    raw = os.getenv("MAX_PACKETS", "").strip()
    if not raw:
        return None

    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"MAX_PACKETS must be an integer, got: {raw!r}")

    if value <= 0:
        raise ValueError(f"MAX_PACKETS must be > 0, got: {value}")

    return value


def main():
    pcap_path = os.getenv("PCAP_FILE", "examples/sample.pcap")
    metrics_port = int(os.getenv("METRICS_PORT", "9100"))
    max_packets = _read_max_packets()

    start_http_server(metrics_port)
    print(f"Metrics server running on http://localhost:{metrics_port}/metrics")
    print(f"Reading PCAP: {pcap_path}")
    if max_packets is None:
        print("MAX_PACKETS: not set (processing full PCAP)")
    else:
        print(f"MAX_PACKETS: {max_packets}")

    # Elasticsearch setup
    es = create_es_client()
    index_name = get_index_name()
    print(f"Elasticsearch target: {os.getenv('ELASTIC_URL')} | index: {index_name}")

    processed = 0

    for pkt in iter_packets(pcap_path):
        doc = packet_to_document(pkt)

        # Metrics: packets + bytes by protocol
        proto = normalize_protocol(doc.get("l4_protocol", "other"))
        pcap_packets_total.labels(protocol=proto).inc()

        pkt_len = doc.get("packet_length")
        if isinstance(pkt_len, int):
            pcap_bytes_total.labels(protocol=proto).inc(pkt_len)

        # Write to Elasticsearch + metric success/fail
        ok = write_document(es, index_name, doc, retries=3, backoff_seconds=0.5)
        if ok:
            pcap_elastic_write_total.labels(status="success").inc()
        else:
            pcap_elastic_write_total.labels(status="fail").inc()

        processed += 1

        # Stop condition (only if MAX_PACKETS set)
        if max_packets is not None and processed >= max_packets:
            break

    print(f"Done. Total packets processed: {processed}")
    print("Entering idle mode (Ctrl+C to stop)...")

    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()

