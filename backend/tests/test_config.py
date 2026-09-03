from pathlib import Path

from app import config


CONFIG_NAMES = (
    "DATABASE_URL",
    "UPLOAD_DIR",
    "REPORT_DIR",
    "CORS_ORIGINS",
    "UPLOAD_MAX_BYTES",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_TIMEOUT_SECONDS",
    "APP_HOST",
    "APP_PORT",
    "APP_WORKERS",
    "APP_LOG_LEVEL",
    "AUTH_MODE",
    "APP_ACCESS_TOKEN",
    "RATE_LIMIT_WINDOW_SECONDS",
    "UPLOAD_RATE_LIMIT",
    "AI_RATE_LIMIT",
    "TRUST_PROXY_HEADERS",
    "TRUSTED_PROXY_IPS",
)


def clear_config(monkeypatch):
    for name in CONFIG_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "dotenv_values", lambda _path: {})


def test_runtime_config_keeps_local_defaults(monkeypatch):
    clear_config(monkeypatch)

    assert config.get_database_url() == "sqlite:///./bid.db"
    assert config.get_upload_dir() == Path("uploads")
    assert config.get_report_dir() == Path("reports")
    assert config.get_cors_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert config.get_upload_max_bytes() == 50 * 1024 * 1024
    assert config.get_deepseek_model("deepseek-chat") == "deepseek-chat"
    assert config.get_deepseek_timeout_seconds() == 60.0
    assert config.get_app_host() == "127.0.0.1"
    assert config.get_app_port() == 8000
    assert config.get_app_workers() == 1
    assert config.get_app_log_level() == "info"
    assert config.get_auth_mode() == "disabled"
    assert config.get_app_access_token() == ""
    assert config.get_rate_limit_window_seconds() == 60
    assert config.get_upload_rate_limit() == 30
    assert config.get_ai_rate_limit() == 60
    assert config.trust_proxy_headers() is False
    assert config.get_trusted_proxy_ips() == {"127.0.0.1", "::1"}


def test_runtime_config_uses_process_environment(monkeypatch):
    clear_config(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./runtime/custom.db")
    monkeypatch.setenv("UPLOAD_DIR", "runtime/uploads")
    monkeypatch.setenv("REPORT_DIR", "runtime/reports")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        " https://bid.example.com,https://admin.example.com, ",
    )
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "1048576")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deployment-model")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("APP_HOST", "0.0.0.0")
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("APP_WORKERS", "2")
    monkeypatch.setenv("APP_LOG_LEVEL", "warning")
    monkeypatch.setenv("AUTH_MODE", "shared_token")
    monkeypatch.setenv("APP_ACCESS_TOKEN", "a" * 32)
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "120")
    monkeypatch.setenv("UPLOAD_RATE_LIMIT", "8")
    monkeypatch.setenv("AI_RATE_LIMIT", "12")
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.1, 10.0.0.2")

    assert config.get_database_url() == "sqlite:///./runtime/custom.db"
    assert config.get_upload_dir() == Path("runtime/uploads")
    assert config.get_report_dir() == Path("runtime/reports")
    assert config.get_cors_origins() == [
        "https://bid.example.com",
        "https://admin.example.com",
    ]
    assert config.get_upload_max_bytes() == 1048576
    assert config.get_deepseek_model("fallback-model") == "deployment-model"
    assert config.get_deepseek_timeout_seconds() == 45.5
    assert config.get_app_host() == "0.0.0.0"
    assert config.get_app_port() == 9000
    assert config.get_app_workers() == 2
    assert config.get_app_log_level() == "warning"
    assert config.get_auth_mode() == "shared_token"
    assert config.get_app_access_token() == "a" * 32
    assert config.get_rate_limit_window_seconds() == 120
    assert config.get_upload_rate_limit() == 8
    assert config.get_ai_rate_limit() == 12
    assert config.trust_proxy_headers() is True
    assert config.get_trusted_proxy_ips() == {"10.0.0.1", "10.0.0.2"}


def test_invalid_positive_limits_fall_back(monkeypatch):
    clear_config(monkeypatch)
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "0")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "not-a-number")
    monkeypatch.setenv("APP_PORT", "70000")
    monkeypatch.setenv("APP_WORKERS", "0")
    monkeypatch.setenv("APP_LOG_LEVEL", "verbose")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "0")
    monkeypatch.setenv("UPLOAD_RATE_LIMIT", "invalid")

    assert config.get_upload_max_bytes() == 50 * 1024 * 1024
    assert config.get_deepseek_timeout_seconds() == 60.0
    assert config.get_app_port() == 8000
    assert config.get_app_workers() == 1
    assert config.get_app_log_level() == "info"
    assert config.get_rate_limit_window_seconds() == 60
    assert config.get_upload_rate_limit() == 30


def test_runtime_config_uses_backend_env_before_project_env(monkeypatch):
    for name in CONFIG_NAMES:
        monkeypatch.delenv(name, raising=False)

    def fake_dotenv_values(path):
        if path == config.BACKEND_ROOT / ".env":
            return {"UPLOAD_DIR": "backend-uploads"}
        return {"UPLOAD_DIR": "project-uploads", "REPORT_DIR": "project-reports"}

    monkeypatch.setattr(config, "dotenv_values", fake_dotenv_values)

    assert config.get_upload_dir() == Path("backend-uploads")
    assert config.get_report_dir() == Path("project-reports")
