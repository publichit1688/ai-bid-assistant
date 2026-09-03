import json
import logging
import re
import sys
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "database_url",
    "password",
    "secret",
    "secret_key",
    "token",
}
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{6,}\b", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
)


def is_sensitive_key(key):
    normalized = str(key).lower()
    return normalized in SENSITIVE_KEYS or normalized.endswith(
        ("_api_key", "_password", "_secret", "_secret_key", "_token")
    )


def redact_sensitive(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if is_sensitive_key(key) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    return value


def normalize_request_id(value):
    candidate = (value or "").strip()
    return candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex


def normalize_log_path(path):
    if path.startswith("/uploads/"):
        return "/uploads/<file>"
    normalized = re.sub(r"(?<=/)\d+(?=/|$)", "{id}", path)
    return redact_sensitive(normalized[:256])


def configure_access_logger():
    access_logger = logging.getLogger("ai_bid_assistant.access")
    if not access_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        access_logger.addHandler(handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    return access_logger


logger = configure_access_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            event = {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "route": normalize_log_path(request.url.path),
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            logger.info(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
