from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_SOURCE = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
API_SOURCE = PROJECT_ROOT / "frontend" / "src" / "api.js"


def test_frontend_uses_one_memory_only_authenticated_client():
    app_content = APP_SOURCE.read_text(encoding="utf-8")
    api_content = API_SOURCE.read_text(encoding="utf-8")

    assert 'from "./api"' in app_content
    assert 'from "axios"' not in app_content
    assert "apiClient.interceptors.request.use" in api_content
    assert "config.headers.Authorization" in api_content
    assert 'new Event("app-auth-required")' in api_content
    assert "localStorage" not in api_content
    assert "sessionStorage" not in api_content
    assert "console." not in api_content
    assert "console." not in app_content


def test_pdf_and_report_paths_share_the_authenticated_client():
    app_content = APP_SOURCE.read_text(encoding="utf-8")

    required_paths = (
        "/api/files",
        "/api/dashboard",
        "/api/dashboard/ai-summary",
        "/api/upload",
        "/api/report",
        "/api/compare/ai-decision",
        "/api/compare-report",
    )
    for path in required_paths:
        assert path in app_content

    assert "loadProtectedPdf" in app_content
    assert 'responseType:"blob"' in app_content
    assert "window.URL.createObjectURL(response.data)" in app_content
    assert "凭据仅保存在当前页面内存中" in app_content
    credential_effect = app_content.split("if(!credentialConfigured){", 1)[1].split(
        "},[credentialConfigured]);", 1
    )[0]
    assert "loadFiles();" in credential_effect
    assert "loadDashboard();" in credential_effect
