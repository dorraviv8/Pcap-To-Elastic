import os
import time
from typing import Any, Dict, Optional

from elasticsearch import Elasticsearch


def create_es_client() -> Elasticsearch:
    url = os.getenv("ELASTIC_URL", "http://localhost:9200")
    username = os.getenv("ELASTIC_USERNAME")
    password = os.getenv("ELASTIC_PASSWORD")

    if username and password:
        return Elasticsearch(url, basic_auth=(username, password))
    return Elasticsearch(url)


def get_index_name() -> str:
    return os.getenv("ELASTIC_INDEX", "pcap-packets")


def write_document(
    es: Elasticsearch,
    index: str,
    doc: Dict[str, Any],
    retries: int = 3,
    backoff_seconds: float = 0.5,
) -> bool:
    """
    Write one document to Elasticsearch with basic retry.
    Returns True on success, False on final failure.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            es.index(index=index, document=doc)
            return True
        except Exception as e:
            last_error = e
            # basic backoff
            time.sleep(backoff_seconds * attempt)

    # If we got here, all attempts failed
    print(f"[ERROR] Failed to write doc to Elasticsearch after {retries} retries. Last error: {last_error}")
    return False

