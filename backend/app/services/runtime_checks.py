import os
import tempfile

from sqlalchemy import text

from app.config import (
    get_app_access_token,
    get_auth_mode,
    get_report_dir,
    get_upload_dir,
)
from app.database import engine


def check_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_writable_directory(path):
    directory = path.resolve()
    if not directory.is_dir() or not os.access(directory, os.W_OK):
        return False
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".health-",
            dir=directory,
            delete=True,
        ):
            pass
        return True
    except OSError:
        return False


def check_auth_configuration():
    mode = get_auth_mode()
    if mode == "disabled":
        return True
    if mode == "shared_token":
        return len(get_app_access_token()) >= 32
    return False


def readiness_report():
    checks = {
        "database": "ok" if check_database() else "error",
        "upload_storage": (
            "ok" if check_writable_directory(get_upload_dir()) else "error"
        ),
        "report_storage": (
            "ok" if check_writable_directory(get_report_dir()) else "error"
        ),
        "auth_configuration": "ok" if check_auth_configuration() else "error",
    }
    ready = all(status == "ok" for status in checks.values())
    return {
        "status": "ready" if ready else "degraded",
        "service": "AI Bid Assistant",
        "checks": checks,
    }


def prepare_and_validate_runtime():
    get_upload_dir().mkdir(parents=True, exist_ok=True)
    get_report_dir().mkdir(parents=True, exist_ok=True)
    report = readiness_report()
    if report["status"] != "ready":
        failed = [name for name, status in report["checks"].items() if status != "ok"]
        raise RuntimeError("启动检查失败: " + ", ".join(failed))
    return report
