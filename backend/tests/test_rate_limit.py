from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.rate_limit import (
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
    client_identity,
)
from app.services.request_logging import RequestLoggingMiddleware


def test_sliding_window_returns_retry_and_recovers_after_window():
    limiter = SlidingWindowRateLimiter()

    assert limiter.check("client", limit=2, window_seconds=10, now=100) == (True, 0)
    assert limiter.check("client", limit=2, window_seconds=10, now=101) == (True, 0)
    assert limiter.check("client", limit=2, window_seconds=10, now=102) == (False, 8)
    assert limiter.check("client", limit=2, window_seconds=10, now=111) == (True, 0)


def test_proxy_header_is_used_only_for_explicitly_trusted_peer():
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"X-Forwarded-For": "203.0.113.7, 127.0.0.1"},
    )
    direct_identity = client_identity(request, use_proxy_headers=False)
    trusted_identity = client_identity(
        request,
        use_proxy_headers=True,
        trusted_proxies={"127.0.0.1"},
    )
    untrusted_identity = client_identity(
        request,
        use_proxy_headers=True,
        trusted_proxies={"10.0.0.1"},
    )

    assert trusted_identity != direct_identity
    assert untrusted_identity == direct_identity


def build_limited_app(monkeypatch):
    from app.services import rate_limit

    monkeypatch.setattr(rate_limit, "get_upload_rate_limit", lambda: 1)
    monkeypatch.setattr(rate_limit, "get_ai_rate_limit", lambda: 1)
    monkeypatch.setattr(rate_limit, "get_rate_limit_window_seconds", lambda: 60)
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/api/upload")
    def upload():
        return {"ok": True}

    @app.post("/api/compare/ai-decision")
    def compare():
        return {"ok": True}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


def test_limited_route_returns_stable_429_and_retry_after(monkeypatch):
    with TestClient(build_limited_app(monkeypatch)) as client:
        first = client.post("/api/upload")
        limited = client.post("/api/upload")

    assert first.status_code == 200
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    assert limited.headers["X-Request-ID"]
    assert limited.json() == {
        "detail": {
            "code": "RATE_LIMITED",
            "message": "请求过于频繁，请稍后重试。",
        }
    }


def test_ai_routes_share_budget_while_health_is_unlimited(monkeypatch):
    with TestClient(build_limited_app(monkeypatch)) as client:
        assert client.post("/api/compare/ai-decision").status_code == 200
        assert client.post("/api/compare/ai-decision").status_code == 429
        assert [client.get("/api/health").status_code for _ in range(3)] == [200, 200, 200]
