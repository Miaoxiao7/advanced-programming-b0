"""Minimal HTTP server that exposes the summary service on localhost."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Type

from b0_stats.service import JSON_CONTENT_TYPE, handle

MAX_BODY_BYTES = 1_000_000
HTML_CONTENT_TYPE = "text/html; charset=utf-8"
DEMO_ROUTES = ("/", "/demo")
DEMO_FILE = Path(__file__).with_name("demo.html")


def demo_page() -> str:
    """Return the static demo page stored next to this module."""
    return DEMO_FILE.read_text(encoding="utf-8")


class SummaryHandler(BaseHTTPRequestHandler):
    """Map GET and POST onto b0_stats.service.handle."""

    server_version = "B0Stats/0.1"
    max_body_bytes = MAX_BODY_BYTES

    def do_GET(self) -> None:  # noqa: N802
        self._respond("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._respond("POST")

    def log_message(self, format_string: str, *args: Any) -> None:
        return None

    def _content_length(self) -> Optional[int]:
        raw = self.headers.get("Content-Length") or "0"
        try:
            return int(raw)
        except ValueError:
            return None

    def _respond(self, method: str) -> None:
        route = self.path.split("?", 1)[0]
        if method == "GET" and route in DEMO_ROUTES:
            self._write_html(demo_page())
            return
        length = self._content_length()
        if length is None:
            self._write(400, {"error": "invalid_length", "message": "bad header"})
            return
        if length > self.max_body_bytes:
            self._write(413, {"error": "body_too_large", "message": "body too large"})
            return
        body = self.rfile.read(length) if length else b""
        status, payload = handle(method, self.path, body)
        self._write(status, payload)

    def _write(self, status: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _write_html(self, document: str) -> None:
        raw = document.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", HTML_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)


def make_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    handler_class: Type[SummaryHandler] = SummaryHandler,
) -> ThreadingHTTPServer:
    """Create a server; port 0 lets the operating system pick a free port."""
    return ThreadingHTTPServer((host, port), handler_class)


def main() -> None:
    parser = argparse.ArgumentParser(description="B0 summary statistics service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    host, port = server.server_address[:2]
    print("ready: listening on http://{}:{}".format(host, port), flush=True)
    print("demo: http://{}:{}/".format(host, port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
