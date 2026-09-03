import os
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _config_value(name, default=""):
    """Read non-empty process, backend .env, or project .env values."""
    process_value = os.getenv(name)
    if process_value is not None and str(process_value).strip():
        return str(process_value).strip()

    for env_path in (BACKEND_ROOT / ".env", PROJECT_ROOT / ".env"):
        file_value = dotenv_values(env_path).get(name)
        if file_value is not None and str(file_value).strip():
            return str(file_value).strip()
    return default


def get_database_url():
    return _config_value("DATABASE_URL", "sqlite:///./bid.db")


def get_upload_dir():
    return Path(_config_value("UPLOAD_DIR", "uploads"))


def get_report_dir():
    return Path(_config_value("REPORT_DIR", "reports"))


def get_cors_origins():
    raw_value = _config_value(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]


def _positive_number(name, default, cast):
    try:
        value = cast(_config_value(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def get_upload_max_bytes():
    return _positive_number("UPLOAD_MAX_BYTES", 50 * 1024 * 1024, int)


def get_deepseek_api_key():
    return _config_value("DEEPSEEK_API_KEY")


def get_deepseek_base_url():
    return _config_value("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def get_deepseek_timeout_seconds():
    return _positive_number("DEEPSEEK_TIMEOUT_SECONDS", 60.0, float)


def get_deepseek_model(default):
    return _config_value("DEEPSEEK_MODEL", default)


def get_app_host():
    return _config_value("APP_HOST", "127.0.0.1")


def get_app_port():
    port = _positive_number("APP_PORT", 8000, int)
    return port if port <= 65535 else 8000


def get_app_workers():
    return _positive_number("APP_WORKERS", 1, int)


def get_app_log_level():
    value = _config_value("APP_LOG_LEVEL", "info").lower()
    return value if value in {"critical", "error", "warning", "info", "debug"} else "info"


def get_auth_mode():
    return _config_value("AUTH_MODE", "disabled").lower()


def get_app_access_token():
    return _config_value("APP_ACCESS_TOKEN")


def get_rate_limit_window_seconds():
    return _positive_number("RATE_LIMIT_WINDOW_SECONDS", 60, int)


def get_upload_rate_limit():
    return _positive_number("UPLOAD_RATE_LIMIT", 30, int)


def get_ai_rate_limit():
    return _positive_number("AI_RATE_LIMIT", 60, int)


def trust_proxy_headers():
    return _config_value("TRUST_PROXY_HEADERS", "false").lower() in {"1", "true", "yes"}


def get_trusted_proxy_ips():
    raw_value = _config_value("TRUSTED_PROXY_IPS", "127.0.0.1,::1")
    return {item.strip() for item in raw_value.split(",") if item.strip()}
