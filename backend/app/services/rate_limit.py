import hashlib
import ipaddress
import math
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import (
    get_ai_rate_limit,
    get_rate_limit_window_seconds,
    get_trusted_proxy_ips,
    get_upload_rate_limit,
    trust_proxy_headers,
)


LIMITED_ROUTES = {
    ("POST", "/api/upload"): "upload",
    ("POST", "/api/compare/ai-decision"): "ai",
    ("POST", "/api/dashboard/ai-summary"): "ai",
}


def route_category(method, path):
    category = LIMITED_ROUTES.get((method, path))
    if (
        category is None
        and method == "POST"
        and path.startswith("/api/workspaces/")
        and path.endswith(("/outline-suggestions", "/criteria-extractions"))
    ):
        return "ai"
    return category


class SlidingWindowRateLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key, limit, window_seconds, now=None):
        current = time.monotonic() if now is None else now
        cutoff = current - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, math.ceil(events[0] + window_seconds - current))
                return False, retry_after
            events.append(current)
            return True, 0


def client_identity(request, use_proxy_headers=None, trusted_proxies=None):
    direct_host = request.client.host if request.client else "unknown"
    use_proxy = trust_proxy_headers() if use_proxy_headers is None else use_proxy_headers
    proxies = get_trusted_proxy_ips() if trusted_proxies is None else trusted_proxies
    identity = direct_host
    if use_proxy and direct_host in proxies:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        try:
            identity = str(ipaddress.ip_address(forwarded))
        except ValueError:
            identity = direct_host
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter=None):
        super().__init__(app)
        self.limiter = limiter or SlidingWindowRateLimiter()

    async def dispatch(self, request, call_next):
        category = route_category(request.method, request.url.path)
        if not category:
            return await call_next(request)

        limit = get_upload_rate_limit() if category == "upload" else get_ai_rate_limit()
        window = get_rate_limit_window_seconds()
        identity = client_identity(request)
        allowed, retry_after = self.limiter.check(
            f"{category}:{identity}",
            limit,
            window,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "detail": {
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后重试。",
                    }
                },
            )
        return await call_next(request)
