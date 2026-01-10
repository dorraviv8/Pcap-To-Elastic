import os
import time
import logging
from typing import Any, Optional

from elasticsearch import Elasticsearch


logger = logging.getLogger("pcap-app.elastic")


def create_es_client() -> Elasticsearch:
    url = os.getenv("ELASTIC_URL", "http://localhost:9200")
    username = os.getenv("ELASTIC_USERNAME")
    password = os.getenv("ELASTIC_PASSWORD")

    if username and password:
        logger.info("Creating Elasticsearch client with basic auth (url=%s)", url)
        return Elasticsearch(url, basic_auth=(username, password))
    else:
        logger.info("Creating Elasticsearch client (url=%s) ללא auth", url)
        return Elasticsearch(url)


def get_index_name() -> str:
   return os.getenv("ELASTIC_INDEX", "pcap-packets")


def write_document(
    es: Elasticsearch,
    index_name: str,
    doc: dict[str, Any],
    retries: int = 3,
    backoff_seconds: float = 0.5,
) -> bool:
    """
    Writes a single document to Elasticsearch with basic retry.
    Returns True on success, False on final failure.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, retries + 2):  # retries=3 => attempts 1..4
        try:
            logger.debug("Writing doc to Elasticsearch (index=%s attempt=%d)", index_name, attempt)

            es.index(index=index_name, document=doc)

            logger.info("Elasticsearch write success (index=%s attempt=%d)", index_name, attempt)
            return True

        except Exception as e:
            last_exc = e
            if attempt <= retries:
                sleep_for = backoff_seconds * attempt  
                logger.warning(
                    "Elasticsearch write failed (index=%s attempt=%d/%d). "
                    "Retrying in %.2fs. Error=%s",
                    index_name,
                    attempt,
                    retries + 1,
                    sleep_for,
                    repr(e),
                )
                time.sleep(sleep_for)
            else:
                logger.error(
                    "Elasticsearch write failed FINAL (index=%s attempts=%d). Error=%s",
                    index_name,
                    retries + 1,
                    repr(e),
                )

    return False

def check_elasticsearch(es: Elasticsearch, timeout_seconds: float = 1.0) -> tuple[bool, str]:
    """
    Lightweight readiness check.
    Returns (True, reason) if ES responds to ping; otherwise (False, error/reason).
    """
    try:
        ok = es.ping(request_timeout=timeout_seconds)
        return (ok, "ping_ok" if ok else "ping_failed")
    except Exception as e:
        return (False, repr(e))

