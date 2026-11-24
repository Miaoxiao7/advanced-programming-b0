"""Contract tests for b0_stats.service.handle, without opening a socket."""

import json
import unittest
from typing import Any, Dict, Optional

from b0_stats.service import handle


def body(payload: Optional[Dict[str, Any]] = None) -> bytes:
    return json.dumps(payload or {}).encode("utf-8")


class HealthRouteTest(unittest.TestCase):
    def test_health_returns_ok(self):
        status, payload = handle("GET", "/health", b"")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("service", payload)

    def test_health_with_query_string(self):
        status, _ = handle("GET", "/health?probe=1", b"")
        self.assertEqual(status, 200)

    def test_post_to_health_is_rejected(self):
        status, payload = handle("POST", "/health", body({"values": [1, 2]}))
        self.assertEqual(status, 405)
        self.assertEqual(payload["error"], "method_not_allowed")


class SummaryRouteTest(unittest.TestCase):
    def test_valid_payload_returns_summary(self):
        status, payload = handle("POST", "/api/summary", body({"values": [1, 2, 3, 4]}))
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 4)
        self.assertAlmostEqual(payload["mean"], 2.5, places=6)

    def test_trailing_slash_is_normalised(self):
        status, payload = handle("POST", "/api/summary/", body({"values": [1, 2]}))
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 2)

    def test_unknown_field_is_ignored(self):
        status, payload = handle(
            "POST",
            "/api/summary",
            body({"values": [1, 2], "note": "extra key"}),
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 2)

    def test_get_on_summary_route_is_rejected(self):
        status, _ = handle("GET", "/api/summary", b"")
        self.assertEqual(status, 405)

    def test_other_method_is_rejected(self):
        status, _ = handle("DELETE", "/api/summary", b"")
        self.assertEqual(status, 405)

    def test_empty_body(self):
        status, payload = handle("POST", "/api/summary", b"")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "missing_body")

    def test_broken_json(self):
        status, payload = handle("POST", "/api/summary", b"{")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_json")

    def test_non_utf8_body(self):
        status, payload = handle("POST", "/api/summary", b"\xff\xfe")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_json")

    def test_payload_without_values(self):
        status, payload = handle("POST", "/api/summary", body({"data": [1, 2]}))
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "missing_values")

    def test_payload_is_not_an_object(self):
        status, payload = handle("POST", "/api/summary", b"[1, 2, 3]")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "missing_values")

    def test_domain_error_is_propagated(self):
        status, payload = handle("POST", "/api/summary", body({"values": []}))
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "empty_input")


class RoutingTest(unittest.TestCase):
    def test_unknown_route(self):
        status, payload = handle("GET", "/api/nothing", b"")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not_found")

    def test_root_route_is_unknown(self):
        status, payload = handle("GET", "/", b"")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
