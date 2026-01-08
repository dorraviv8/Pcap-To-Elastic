from pcap_reader import iter_packets, packet_to_document


def main():
    pcap_path = "examples/sample.pcap"
    print(f"Opening PCAP: {pcap_path}")

    for i, pkt in enumerate(iter_packets(pcap_path)):
        doc = packet_to_document(pkt)

        print("=" * 60)
        print(f"Packet #{i + 1}")
        print(doc)

        if i >= 4:
            break


if __name__ == "__main__":
    main()

