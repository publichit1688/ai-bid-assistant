from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.services import auth
from app.services.auth import SharedTokenAuthMiddleware
from app.services.request_logging import RequestLoggingMiddleware


def build_client():
    app = FastAPI()

    @app.get("/")
    def root():
        return {"status": "public"}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/health/ready")
    def ready():
        return {"status": "ready"}

    @app.get("/uploads/sample.pdf")
    def uploaded_file():
        return {"status": "protected"}

    app.add_middleware(SharedTokenAuthMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return TestClient(app)


def set_auth(monkeypatch, mode="shared_token", token="x" * 32):
    monkeypatch.setattr(auth, "get_auth_mode", lambda: mode)
    monkeypatch.setattr(auth, "get_app_access_token", lambda: token)


def test_disabled_mode_keeps_local_development_compatible(monkeypatch):
    set_auth(monkeypatch, mode="disabled", token="")

    response = build_client().get("/api/health/ready")

    assert response.status_code == 200


def test_shared_token_protects_business_and_upload_routes(monkeypatch):
    token = "shared-deployment-access-token-1234"
    set_auth(monkeypatch, token=token)
    client = build_client()

    missing = client.get("/api/health/ready")
    wrong = client.get("/uploads/sample.pdf", headers={"Authorization": "Bearer wrong"})
    accepted = client.get(
        "/uploads/sample.pdf", headers={"Authorization": f"Bearer {token}"}
    )

    assert missing.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert missing.headers["X-Request-ID"]
    assert missing.json() == {
        "detail": {"code": "AUTH_REQUIRED", "message": "需要有效访问凭据。"}
    }
    assert wrong.status_code == 401
    assert accepted.status_code == 200


def test_root_and_liveness_remain_public(monkeypatch):
    set_auth(monkeypatch)
    client = build_client()

    assert client.get("/").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_invalid_server_configuration_fails_closed_without_secret(monkeypatch):
    short_secret = "secret123"
    set_auth(monkeypatch, token=short_secret)

    response = build_client().get(
        "/api/health/ready", headers={"Authorization": f"Bearer {short_secret}"}
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "AUTH_NOT_CONFIGURED",
            "message": "访问控制配置无效，请联系管理员。",
        }
    }
    assert short_secret not in response.text


def test_cors_preflight_does_not_require_token(monkeypatch):
    set_auth(monkeypatch)

    response = build_client().options(
        "/api/health/ready",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
