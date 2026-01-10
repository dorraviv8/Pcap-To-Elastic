import os
import time
import logging
from http_server import start_observability_server
from pcap_reader import iter_packets, packet_to_document
from metrics import (
    pcap_packets_total,
    pcap_bytes_total,
    pcap_elastic_write_total,
    normalize_protocol,
)
from elastic_writer import create_es_client, get_index_name, write_document, check_elasticsearch


def setup_logging() -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("elastic_transport").setLevel(logging.WARNING)

    logger = logging.getLogger("pcap-app")
    logger.info("Logging initialized (LOG_LEVEL=%s)", level_name)
    return logger


def read_max_packets() -> int | None:
    raw = os.getenv("MAX_PACKETS", "").strip()
    if not raw:
        return None

    try:
        value = int(raw)
    except ValueError as e:
        raise ValueError(f"MAX_PACKETS must be an integer, got: {raw!r}") from e

    if value <= 0:
        raise ValueError(f"MAX_PACKETS must be > 0, got: {value}")

    return value


def main():
    logger = setup_logging()

    pcap_path = os.getenv("PCAP_FILE", "examples/sample.pcap")
    metrics_port = int(os.getenv("METRICS_PORT", "9100"))
    max_packets = read_max_packets()

    es = create_es_client()
    index_name = get_index_name()
    logger.info("Elasticsearch target: %s | index: %s", os.getenv("ELASTIC_URL"), index_name)

    # Observability server (metrics + health + readiness)
    def readiness_check():
        ok, reason = check_elasticsearch(es, timeout_seconds=1.0)
        return ok, {
            "elasticsearch": {"ok": ok, "reason": reason},
            "index": index_name,
        }

    start_observability_server(metrics_port, readiness_check)


    logger.info("Metrics server running on http://localhost:%s/metrics", metrics_port)
    logger.info("Reading PCAP: %s", pcap_path)

    if max_packets is None:
        logger.info("MAX_PACKETS: not set (processing full PCAP)")
    else:
        logger.info("MAX_PACKETS: %s", max_packets)

    # Elasticsearch setup
    es = create_es_client()
    index_name = get_index_name()
    logger.info("Elasticsearch target: %s | index: %s", os.getenv("ELASTIC_URL"), index_name)

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
        if max_packets is not None and processed >= max_packets:
            break

    logger.info("Done. Total packets processed: %s", processed)
    logger.info("Entering idle mode (Ctrl+C to stop)...")

    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()

