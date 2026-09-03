import pytest

from app.services.ai_errors import AIConfigurationError, AIResponseFormatError


class ProviderTimeoutError(Exception):
    pass


ERROR_CASES = [
    (
        AIConfigurationError("missing key sk-test-secret"),
        503,
        "AI_NOT_CONFIGURED",
    ),
    (
        ProviderTimeoutError("timeout with sk-test-secret"),
        504,
        "AI_TIMEOUT",
    ),
    (
        AIResponseFormatError("invalid JSON sk-test-secret"),
        502,
        "AI_INVALID_RESPONSE",
    ),
]


def raise_error(error):
    def _raise(*args, **kwargs):
        raise error

    return _raise


def assert_safe_ai_error(response, status_code, code):
    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code
    assert response.json()["detail"]["message"]
    assert "sk-test-secret" not in response.text


@pytest.mark.parametrize(("error", "status_code", "code"), ERROR_CASES)
def test_compare_ai_errors_are_structured(
    client, monkeypatch, error, status_code, code
):
    from app.api import compare

    monkeypatch.setattr(compare, "analyze_compare_decision", raise_error(error))

    response = client.post("/api/compare/ai-decision", json={})

    assert_safe_ai_error(response, status_code, code)


@pytest.mark.parametrize(("error", "status_code", "code"), ERROR_CASES)
def test_dashboard_ai_errors_are_structured(
    client, monkeypatch, error, status_code, code
):
    from app.api import dashboard

    monkeypatch.setattr(dashboard, "analyze_dashboard_management", raise_error(error))

    response = client.post(
        "/api/dashboard/ai-summary",
        json={"days": 7, "total_projects": 123},
    )

    assert_safe_ai_error(response, status_code, code)


@pytest.mark.parametrize(("error", "status_code", "code"), ERROR_CASES)
def test_upload_ai_errors_are_structured_without_database_records(
    client, isolated_app, monkeypatch, error, status_code, code
):
    from app.api import upload
    from app.models import BidFile

    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: [{"page": 1, "text": "脱敏测试内容"}],
    )
    monkeypatch.setattr(upload, "analyze_bid", raise_error(error))

    response = client.post(
        "/api/upload",
        files={"file": ("ai-error-fixture.pdf", b"%PDF-test", "application/pdf")},
    )

    assert_safe_ai_error(response, status_code, code)
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    session = isolated_app["session_factory"]()
    try:
        assert session.query(BidFile).count() == 0
    finally:
        session.close()
