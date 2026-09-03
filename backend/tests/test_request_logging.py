import json
import re

from app.services.request_logging import (
    normalize_log_path,
    normalize_request_id,
    redact_sensitive,
)


def test_redact_sensitive_handles_nested_fields_and_token_patterns():
    result = redact_sensitive(
        {
            "api_key": "should-not-appear",
            "DEEPSEEK_API_KEY": "also-hidden",
            "nested": {
                "authorization": "Bearer abc.def.ghi",
                "message": "provider rejected sk-test-secret-value",
            },
            "safe": "kept",
        }
    )

    assert result == {
        "api_key": "[REDACTED]",
        "DEEPSEEK_API_KEY": "[REDACTED]",
        "nested": {
            "authorization": "[REDACTED]",
            "message": "provider rejected [REDACTED]",
        },
        "safe": "kept",
    }


def test_request_id_accepts_only_bounded_safe_characters():
    assert normalize_request_id("trace-123.A_B") == "trace-123.A_B"
    generated = normalize_request_id("bad id with spaces")
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    assert re.fullmatch(r"[0-9a-f]{32}", normalize_request_id("x" * 65))


def test_log_path_hides_file_names_ids_and_token_patterns():
    assert normalize_log_path("/uploads/customer-bid.pdf") == "/uploads/<file>"
    assert normalize_log_path("/api/files/123/preview") == "/api/files/{id}/preview"
    assert normalize_log_path("/unknown/sk-test-secret-value") == "/unknown/[REDACTED]"


def test_access_log_uses_route_template_and_excludes_query(client, monkeypatch):
    from app.services import request_logging

    events = []
    monkeypatch.setattr(request_logging.logger, "info", events.append)

    response = client.get(
        "/api/health?api_key=query-secret",
        headers={"X-Request-ID": "request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"
    assert len(events) == 1
    payload = json.loads(events[0])
    assert payload["event"] == "http_request"
    assert payload["request_id"] == "request-123"
    assert payload["method"] == "GET"
    assert payload["route"] == "/api/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] >= 0
    assert "query-secret" not in events[0]
    assert "api_key" not in events[0]


def test_invalid_incoming_request_id_is_replaced(client, monkeypatch):
    from app.services import request_logging

    events = []
    monkeypatch.setattr(request_logging.logger, "info", events.append)

    response = client.get(
        "/api/health",
        headers={"X-Request-ID": "unsafe id with spaces"},
    )

    request_id = response.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)
    assert json.loads(events[0])["request_id"] == request_id
