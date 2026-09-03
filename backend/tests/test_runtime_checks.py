import pytest


def test_prepare_runtime_creates_and_checks_storage(tmp_path, monkeypatch):
    from app.services import runtime_checks

    upload_dir = tmp_path / "persistent" / "uploads"
    report_dir = tmp_path / "persistent" / "reports"
    monkeypatch.setattr(runtime_checks, "get_upload_dir", lambda: upload_dir)
    monkeypatch.setattr(runtime_checks, "get_report_dir", lambda: report_dir)
    monkeypatch.setattr(runtime_checks, "check_database", lambda: True)

    report = runtime_checks.prepare_and_validate_runtime()

    assert report["status"] == "ready"
    assert upload_dir.is_dir()
    assert report_dir.is_dir()
    assert list(upload_dir.iterdir()) == []
    assert list(report_dir.iterdir()) == []


def test_prepare_runtime_fails_without_exposing_config_values(tmp_path, monkeypatch):
    from app.services import runtime_checks

    upload_dir = tmp_path / "uploads"
    report_dir = tmp_path / "reports"
    monkeypatch.setattr(runtime_checks, "get_upload_dir", lambda: upload_dir)
    monkeypatch.setattr(runtime_checks, "get_report_dir", lambda: report_dir)
    monkeypatch.setattr(runtime_checks, "check_database", lambda: False)

    with pytest.raises(RuntimeError) as exc_info:
        runtime_checks.prepare_and_validate_runtime()

    assert str(exc_info.value) == "启动检查失败: database"


def test_writable_directory_check_rejects_missing_directory(tmp_path):
    from app.services.runtime_checks import check_writable_directory

    assert check_writable_directory(tmp_path / "missing") is False


def test_prepare_runtime_rejects_invalid_auth_without_exposing_token(
    tmp_path, monkeypatch
):
    from app.services import runtime_checks

    secret_value = "do-not-expose-this-access-token-value"
    monkeypatch.setattr(runtime_checks, "get_upload_dir", lambda: tmp_path / "uploads")
    monkeypatch.setattr(runtime_checks, "get_report_dir", lambda: tmp_path / "reports")
    monkeypatch.setattr(runtime_checks, "check_database", lambda: True)
    monkeypatch.setattr(runtime_checks, "get_auth_mode", lambda: "shared_token")
    monkeypatch.setattr(runtime_checks, "get_app_access_token", lambda: secret_value[:10])

    with pytest.raises(RuntimeError) as exc_info:
        runtime_checks.prepare_and_validate_runtime()

    assert str(exc_info.value) == "启动检查失败: auth_configuration"
    assert secret_value not in str(exc_info.value)
