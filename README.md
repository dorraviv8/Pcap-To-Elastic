
# PCAP to Elasticsearch with Prometheus Metrics

A lightweight DevOps-oriented service that **parses a PCAP file**, writes each packet as a document into **Elasticsearch**, and exposes **Prometheus metrics** for observability.

The project runs fully containerized using **Docker Compose** and includes:
- Elasticsearch
- Kibana
- Prometheus
- A custom Python PCAP processing service (`pcap-app`)

## Project Structure

```text
Pcap-To_Elastic/
├── src/
│   ├── main.py               # Orchestrates: read PCAP, update metrics, write to Elasticsearch
│   ├── pcap_reader.py        # Reads packets (stream) and converts each packet to a document (dict)
│   ├── elastic_writer.py     # Elasticsearch client + single-doc write with retry
│   ├── metrics.py            # Prometheus counters definitions + protocol normalization
│   ├── http_server.py        # Serves /metrics, /health, /ready on METRICS_PORT
│   └── pcap_explore.py       # (Optional) exploration/debug script for PCAP (not required)
│
├── examples/
│   └── sample.pcap           # Example PCAP file
│
├── infra/
│   └── prometheus/
│       └── prometheus.yaml   # Prometheus scrape config for the app
│
├── Dockerfile                # Builds the app container image
├── docker-compose.yaml       # Runs Elastic + Kibana + Prometheus + the app
├── requirements.txt          # Python dependencies
└── README.md
```

---

## Requirements

* Docker + Docker Compose
* (Optional for local run) Python 3.9+ and a virtualenv

---

## Run with Docker Compose (Recommended)

### 1) Start the stack

From the project root:

```bash
docker compose up --build
```

This will start:

* Elasticsearch: `http://localhost:9200`
* Kibana: `http://localhost:5601`
* Prometheus: `http://localhost:9090`
* App metrics: `http://localhost:9100/metrics`
* App health: `http://localhost:9100/health`
* App readiness: `http://localhost:9100/ready`

### 2) Verify metrics, health and readiness endpoints

```bash
curl -s http://localhost:9100/metrics | grep pcap_
curl -i http://localhost:9100/health
curl -i http://localhost:9100/ready
```

Expected (example):

* `pcap_packets_total{protocol="tcp"} ...`
* `pcap_bytes_total{protocol="tcp"} ...`
* `pcap_elastic_write_total{status="success"} ...`
* `/health returns 200 {"status":"ok"}`
* `/ready returns 200 ... when Elasticsearch is reachable, otherwise 503 ...`

### 3) Verify documents in Elasticsearch

Count documents:

```bash
curl -s "http://localhost:9200/pcap-packets/_count?pretty"
```

Fetch one document:

```bash
curl -s "http://localhost:9200/pcap-packets/_search?size=1&pretty"
```

### 4) Prometheus queries

Open Prometheus UI: `http://localhost:9090`

Try these queries:

Packets by protocol:
```
sum by (protocol) (pcap_packets_total)
```
Bytes by protocol:
```
sum by (protocol) (pcap_bytes_total)
```
Elastic write failures:
```
pcap_elastic_write_total{status="fail"}
```
---

## Environment Variables

### PCAP input

* `PCAP_FILE` – path to PCAP file inside the container  
  Default (in compose): `/data/sample.pcap`

* `MAX_PACKETS` – optional limit for number of packets to process (useful for demos/testing).  
  If not set, processes the full PCAP.

### Metrics

* `METRICS_PORT` – HTTP port used by the observability server  
  Default: `9100`

The service exposes the following endpoints on the same port:

* `GET /metrics` – Prometheus metrics (scraped by Prometheus)
* `GET /health` – liveness check (returns `200` if the process is running)
* `GET /ready` – readiness check (returns `200` only if Elasticsearch is reachable, otherwise `503`)

### Elasticsearch

* `ELASTIC_URL` – Elasticsearch URL (e.g. `http://elasticsearch:9200`)
* `ELASTIC_INDEX` – index name (e.g. `pcap-packets`)

## Example Elasticsearch Document

A single packet is stored as one document with these fields:

```json
{
  "timestamp": "2026-01-07T12:03:20.385397+00:00",
  "src_ip": "192.168.1.10",
  "dst_ip": "10.0.0.5",
  "src_port": 12345,
  "dst_port": 22,
  "l4_protocol": "tcp",
  "packet_length": 40
}


```

Notes:

* Packets without IP/TCP/UDP (e.g. ARP) are still stored with best-effort fields:

  * `timestamp`, `packet_length`, and protocol `other`

---

## Local Run (Optional)

Create and activate a virtualenv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run:

```bash
export PCAP_FILE=examples/sample.pcap
export METRICS_PORT=9100
export ELASTIC_URL=http://localhost:9200
export ELASTIC_INDEX=pcap-packets

python src/main.py
```

---

## Notes / Improvements for Production

Potential improvements:

* Use Elasticsearch bulk indexing instead of single-document writes
* Better retry
* Index naming by date (e.g. `pcap-packets-YYYY.MM.DD`)

