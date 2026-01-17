from prometheus_client import Counter

pcap_packets_total = Counter(
    "pcap_packets_total",
    "Total number of processed packets by L4 protocol",
    ["protocol"],  # tcp|udp|icmp|other
)

pcap_bytes_total = Counter(
    "pcap_bytes_total",
    "Total number of processed bytes by L4 protocol",
    ["protocol"],  # tcp|udp|icmp|other
)

pcap_elastic_write_total = Counter(
    "pcap_elastic_write_total",
    "Total number of Elasticsearch write attempts",
    ["status"],  # success|fail
)

VALID_PROTOCOLS = {"tcp", "udp", "icmp", "other"}


def normalize_protocol(proto: str) -> str:
    proto = (proto or "other").lower()
    return proto if proto in VALID_PROTOCOLS else "other"

