from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = PROJECT_ROOT / "docs" / "AUTH_DECISION.md"


def test_auth_decision_covers_every_business_route_and_static_files():
    content = DECISION_PATH.read_text(encoding="utf-8")
    required_paths = (
        "/api/health",
        "/api/health/ready",
        "/api/files",
        "/api/files/{file_id}",
        "/api/files/{file_id}/preview",
        "/api/dashboard",
        "/api/upload",
        "/api/dashboard/ai-summary",
        "/api/compare/ai-decision",
        "/api/report",
        "/api/compare-report",
        "/uploads/*",
        "/openapi.json",
    )

    for path in required_paths:
        assert path in content


def test_auth_decision_preserves_disabled_default_and_secret_rules():
    content = DECISION_PATH.read_text(encoding="utf-8")

    assert "AUTH_MODE=disabled|shared_token" in content
    assert "本地默认 `disabled`" in content
    assert "localStorage" in content
    assert "常量时间比较" in content
    assert "后端保护和前端凭据接入已实现" in content
    assert "sk-" not in content
