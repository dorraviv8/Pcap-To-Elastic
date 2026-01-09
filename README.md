### מפת פרויקט (Project Map)

ככה החלקים המרכזיים בפרויקט “מדברים” אחד עם השני:

**זרימת עבודה כללית**

1. `main.py` הוא ה־**entrypoint** (מה שרץ בתוך הקונטיינר).
2. `main.py` קורא packets מה־PCAP דרך `pcap_reader.iter_packets()`
3. לכל packet הוא בונה document אחיד דרך `pcap_reader.packet_to_document()`
4. הוא מעדכן **מטריקות** דרך האובייקטים שהוגדרו ב־`metrics.py`
5. הוא כותב את ה־document ל־Elasticsearch דרך `elastic_writer.write_document()` (כולל retry)
6. Prometheus מגרד את `/metrics` של האפליקציה (פורט 9100) לפי `infra/prometheus/prometheus.yaml`
7. Kibana מאפשר לראות ולשאול את הנתונים שנכתבו ל־Elasticsearch

**מי תלוי במי**

* `main.py` תלוי ב:

  * `pcap_reader.py` (קריאה + הפיכת packet ל-document)
  * `metrics.py` (Counters)
  * `elastic_writer.py` (כתיבה ל־Elastic)
  * `prometheus_client` (שרת /metrics)
* `pcap_reader.py` תלוי ב־`scapy`
* `elastic_writer.py` תלוי ב־`elasticsearch` (Python client)
* `metrics.py` תלוי ב־`prometheus_client`
* `docker-compose.yaml` תלוי ב־Dockerfile של האפליקציה + images רשמיים של Elastic/Kibana/Prometheus

---

## README.md מעודכן (תוכן מלא להדבקה)

הדבק/החלף את `README.md` בשורש הפרויקט בתוכן הבא:

````markdown
# PCAP → Elasticsearch + Prometheus Metrics

This project implements a small service that:
1. Reads a `.pcap` file and processes each packet
2. Writes one document per packet into Elasticsearch
3. Exposes Prometheus metrics at `/metrics`

The goal is to demonstrate:
- Basic networking understanding (packet fields extraction)
- Clean, readable Python code
- Observability thinking (metrics + clear errors)
- Ability to integrate technologies (Scapy + Elasticsearch + Prometheus)

---

## Project Structure

```text
Pcap-To_Elastic/
├── src/
│   ├── main.py               # Orchestrates: read PCAP, update metrics, write to Elasticsearch
│   ├── pcap_reader.py        # Reads packets (stream) and converts each packet to a document (dict)
│   ├── elastic_writer.py     # Elasticsearch client + single-doc write with retry
│   ├── metrics.py            # Prometheus counters definitions + protocol normalization
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
````

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

### 2) Verify metrics endpoint

```bash
curl -s http://localhost:9100/metrics | grep pcap_
```

Expected (example):

* `pcap_packets_total{protocol="tcp"} ...`
* `pcap_bytes_total{protocol="tcp"} ...`
* `pcap_elastic_write_total{status="success"} ...`

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

* `pcap_packets_total`
* `pcap_bytes_total`
* `pcap_elastic_write_total`

---

## Environment Variables

### PCAP input

* `PCAP_FILE` – path to PCAP file inside the container
  Default (in compose): `/data/sample.pcap`

### Metrics

* `METRICS_PORT` – port for `/metrics` endpoint
  Default: `9100`

### Elasticsearch

* `ELASTIC_URL` – Elasticsearch URL (e.g. `http://elasticsearch:9200`)
* `ELASTIC_INDEX` – index name (e.g. `pcap-packets`)
* `ELASTIC_USERNAME` – optional
* `ELASTIC_PASSWORD` – optional

---

## Example Elasticsearch Document

A single packet is stored as one document with these fields:

```json
{
  "timestamp": 1767715400.385397,
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
* Add structured logging (JSON logs)
* Configurable `MAX_PACKETS` (instead of fixed 5)
* Better retry/backoff + dead-letter queue for failed writes
* Index naming by date (e.g. `pcap-packets-YYYY.MM.DD`)
* Unit tests for `packet_to_document()` and writer retry logic

````

---

## מה זה “Parsing” ולמה חזרתי על זה?

**Parsing (פרסינג / ניתוח תחבירי-מבני)** זה תהליך שבו אתה לוקח **קלט גולמי** (Raw Input) ומתרגם אותו ל־**מבנה נתונים מסודר** שקל לעבוד איתו בקוד.

במקרה שלנו:
- הקלט הגולמי הוא packet מתוך PCAP (אובייקט של Scapy שמכיל שכבות שונות)
- ה־parsing שלנו הוא הפעולה של “לפרק” את ה-packet ולהוציא ממנו את השדות שאנחנו צריכים
- התוצר הוא `dict` מסודר כמו:

```python
{
  "timestamp": ...,
  "src_ip": ...,
  "dst_ip": ...,
  "src_port": ...,
  "dst_port": ...,
  "l4_protocol": ...,
  "packet_length": ...
}
````

