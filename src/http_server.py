import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Tuple, Dict, Any
from urllib.parse import urlparse

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


logger = logging.getLogger("pcap-app.http")


def start_observability_server(
    port: int,
    readiness_check: Callable[[], Tuple[bool, Dict[str, Any]]],
    host: str = "0.0.0.0",
) -> ThreadingHTTPServer:
    """
    Starts a small HTTP server that serves:
      - /metrics  (Prometheus format)
      - /health   (always 200 if process is alive)
      - /ready    (200 only if dependencies are ready; otherwise 503)
    Runs in a background thread (daemon).
    """

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path

            if path == "/metrics":
                data = generate_latest()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if path == "/health":
                self._send_json(200, {"status": "ok"})
                return

            if path == "/ready":
                ready, details = readiness_check()
                if ready:
                    self._send_json(200, {"status": "ready", **details})
                else:
                    self._send_json(503, {"status": "not_ready", **details})
                return

            self._send_json(404, {"status": "not_found", "path": path})

        def log_message(self, format, *args):  # silence default http.server logs
            logger.debug("HTTP: " + format, *args)

    server = ThreadingHTTPServer((host, port), Handler)

    import threading

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    logger.info("Observability server started on %s:%d (endpoints: /metrics, /health, /ready)", host, port)
    return server

