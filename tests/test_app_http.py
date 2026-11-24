"""End-to-end checks against a real socket on an ephemeral port."""

import contextlib
import http.client
import io
import json
import socket
import sys
import threading
import unittest
from typing import Any, Dict, Optional, Tuple
from unittest import mock

from b0_stats import app
from b0_stats.app import SummaryHandler, make_server


class TinyLimitHandler(SummaryHandler):
    """Handler with a deliberately small body limit for the 413 check."""

    max_body_bytes = 16


def request(
    port: int,
    method: str,
    path: str,
    payload: Optional[bytes] = None,
) -> Tuple[int, Dict[str, Any]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(
            method,
            path,
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        raw = response.read()
        data = json.loads(raw.decode("utf-8")) if raw else {}
        return response.status, data
    finally:
        connection.close()


def raw_exchange(port: int, payload: bytes) -> bytes:
    """Send bytes verbatim so an invalid header can be reproduced."""
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall(payload)
        chunks = []
        while True:
            try:
                chunk = connection.recv(4096)
            except (ConnectionAbortedError, ConnectionResetError):
                break
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


class _ServerMixin:
    handler_class = SummaryHandler

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = make_server("127.0.0.1", 0, cls.handler_class)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)


class HttpServiceTest(_ServerMixin, unittest.TestCase):
    def test_health_over_http(self):
        status, payload = request(self.port, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_summary_over_http(self):
        status, payload = request(
            self.port,
            "POST",
            "/api/summary",
            json.dumps({"values": [1, 2, 3, 4]}).encode("utf-8"),
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 4)
        self.assertAlmostEqual(payload["mean"], 2.5, places=6)

    def test_broken_json_over_http(self):
        status, payload = request(self.port, "POST", "/api/summary", b"{")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_json")

    def test_unknown_route_over_http(self):
        status, payload = request(self.port, "GET", "/nope")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not_found")


class PayloadLimitTest(_ServerMixin, unittest.TestCase):
    handler_class = TinyLimitHandler

    def test_oversized_body_is_rejected_before_reading(self):
        raw = (
            b"POST /api/summary HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Length: 999\r\n\r\n"
        )
        response = raw_exchange(self.port, raw)
        self.assertIn(b"413", response.split(b"\r\n")[0])
        self.assertIn(b"body_too_large", response)


class BrokenHeaderTest(_ServerMixin, unittest.TestCase):
    def test_invalid_content_length_is_rejected(self):
        raw = (
            b"POST /api/summary HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Length: abc\r\n\r\n"
        )
        response = raw_exchange(self.port, raw)
        self.assertIn(b"400", response.split(b"\r\n")[0])
        self.assertIn(b"invalid_length", response)


class MainTest(unittest.TestCase):
    def test_main_announces_ready_and_closes_server(self):
        fake_server = mock.Mock()
        fake_server.server_address = ("127.0.0.1", 8123)
        fake_server.serve_forever.side_effect = KeyboardInterrupt
        with mock.patch.object(app, "make_server", return_value=fake_server):
            with mock.patch.object(sys, "argv", ["app", "--port", "8123"]):
                with contextlib.redirect_stdout(io.StringIO()) as captured:
                    app.main()
        self.assertIn("ready: listening on http://127.0.0.1:8123", captured.getvalue())
        fake_server.server_close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
