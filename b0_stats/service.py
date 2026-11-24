"""HTTP-independent request handling for the summary service."""

import json
from typing import Any, Dict, Tuple

from b0_stats.stats import StatsError, summarise

JSON_CONTENT_TYPE = "application/json; charset=utf-8"
HEALTH_ROUTE = "/health"
SUMMARY_ROUTE = "/api/summary"
KNOWN_ROUTES = (HEALTH_ROUTE, SUMMARY_ROUTE)


def _error(status: int, code: str, message: str) -> Tuple[int, Dict[str, Any]]:
    return status, {"error": code, "message": message}


def handle(method: str, path: str, body: bytes) -> Tuple[int, Dict[str, Any]]:
    """Return a status code and a JSON-serialisable payload.

    Input validation lives here rather than in the socket handler so the whole
    contract can be checked without opening a port.
    """
    route = path.split("?", 1)[0].rstrip("/") or "/"
    if route not in KNOWN_ROUTES:
        return _error(404, "not_found", "unknown route: {}".format(route))
    if method == "GET":
        if route == HEALTH_ROUTE:
            return 200, {"status": "ok", "service": "b0-stats-summary"}
        return _error(405, "method_not_allowed", "use POST for {}".format(route))
    if method != "POST":
        return _error(405, "method_not_allowed", "{} is not allowed".format(method))
    if route != SUMMARY_ROUTE:
        return _error(405, "method_not_allowed", "use GET for {}".format(route))
    if not body:
        return _error(400, "missing_body", "request body must be JSON")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "invalid_json", "request body is not valid JSON")
    if not isinstance(payload, dict) or "values" not in payload:
        return _error(400, "missing_values", "payload must contain 'values'")
    try:
        return 200, summarise(payload["values"])
    except StatsError as error:
        return _error(400, error.code, error.message)
