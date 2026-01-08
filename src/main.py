import os
import time

from prometheus_client import start_http_server

from pcap_reader import iter_packets, packet_to_document
from metrics import pcap_packets_total, pcap_bytes_total, normalize_protocol


def main():
    pcap_path = os.getenv("PCAP_FILE", "examples/sample.pcap")
    metrics_port = int(os.getenv("METRICS_PORT", "9100"))

    start_http_server(metrics_port)
    print(f"Metrics server running on http://localhost:{metrics_port}/metrics")
    print(f"Reading PCAP: {pcap_path}")

    processed = 0

    for pkt in iter_packets(pcap_path):
        doc = packet_to_document(pkt)

        proto = normalize_protocol(doc.get("l4_protocol", "other"))
        pcap_packets_total.labels(protocol=proto).inc()

        pkt_len = doc.get("packet_length")
        if isinstance(pkt_len, int):
            pcap_bytes_total.labels(protocol=proto).inc(pkt_len)

        processed += 1
        if processed >= 5:
            break

        if processed % 1000 == 0:
            print(f"Processed {processed} packets...")

    print(f"Done. Total packets processed: {processed}")
    print("You can still query /metrics while this process is running.")
    print("Entering idle mode (Ctrl+C to stop)...")

    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
