from __future__ import annotations

from typing import Any, Dict, Iterator, Optional

from datetime import datetime, timezone  # <-- ADDED

from scapy.all import PcapReader
from scapy.layers.inet import IP, TCP, UDP, ICMP


def iter_packets(pcap_path: str) -> Iterator[Any]:
    """
    Stream packets from a PCAP file (memory efficient).
    """
    with PcapReader(pcap_path) as pcap:
        for pkt in pcap:
            yield pkt


def safe_packet_length(pkt: Any) -> Optional[int]:
    """
    Best-effort packet length in bytes.
    """
    try:
        return len(bytes(pkt))
    except Exception:
        return None


def packet_to_document(pkt: Any) -> Dict[str, Any]:
    """
    Convert a Scapy packet into a dict (document) aligned with assignment fields:
    - timestamp
    - src_ip, dst_ip
    - src_port, dst_port
    - l4_protocol: tcp/udp/icmp/other
    - packet_length

    Packets without IP/TCP/UDP are still returned with best-effort fields.
    """
    timestamp = float(getattr(pkt, "time", None)) if getattr(pkt, "time", None) is not None else None

    doc: Dict[str, Any] = {
        "timestamp": timestamp,
        "@timestamp": (
            datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            if isinstance(timestamp, (int, float))
            else None
        ),  # <-- ADDED
        "src_ip": None,
        "dst_ip": None,
        "src_port": None,
        "dst_port": None,
        "l4_protocol": "other",
        "packet_length": safe_packet_length(pkt),
    }

    # IP layer (L3)
    if IP in pkt:
        ip = pkt[IP]
        doc["src_ip"] = getattr(ip, "src", None)
        doc["dst_ip"] = getattr(ip, "dst", None)

        # L4 protocol + ports
        if TCP in pkt:
            tcp = pkt[TCP]
            doc["l4_protocol"] = "tcp"
            doc["src_port"] = int(getattr(tcp, "sport", 0)) if getattr(tcp, "sport", None) is not None else None
            doc["dst_port"] = int(getattr(tcp, "dport", 0)) if getattr(tcp, "dport", None) is not None else None

        elif UDP in pkt:
            udp = pkt[UDP]
            doc["l4_protocol"] = "udp"
            doc["src_port"] = int(getattr(udp, "sport", 0)) if getattr(udp, "sport", None) is not None else None
            doc["dst_port"] = int(getattr(udp, "dport", 0)) if getattr(udp, "dport", None) is not None else None

        elif ICMP in pkt:
            doc["l4_protocol"] = "icmp"

        else:
            doc["l4_protocol"] = "other"

    # No IP layer (e.g., ARP) -> keep defaults + timestamp/length
    return doc

