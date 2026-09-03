import json

def dashboard_payload(**overrides):
    payload = {
        "days": 7,
        "total_projects": 2,
        "total_risks": 5,
        "average_score": 86,
        "risk_distribution": {"high": 1, "middle": 2, "low": 2},
        "score_distribution": {"80_100": 2},
        "period_comparison": {"current_projects": 2},
        "attention_projects": [{"id": 1, "project_name": "脱敏项目"}],
    }
    payload.update(overrides)
    return payload


def generated_summary(sequence):
    return {
        "overall_status": f"替身摘要-{sequence}",
        "risk_change": "稳定",
        "key_attention": "脱敏项目",
        "management_advice": "人工复核",
    }


def cache_rows(isolated_app):
    from app.models import DashboardAICache

    session = isolated_app["session_factory"]()
    try:
        return session.query(DashboardAICache).all()
    finally:
        session.close()


def test_same_normalized_data_hits_cache(client, isolated_app, monkeypatch):
    from app.api import dashboard

    calls = []

    def fake_model(data):
        calls.append(data)
        return generated_summary(len(calls))

    monkeypatch.setattr(dashboard, "analyze_dashboard_management", fake_model)

    first = client.post("/api/dashboard/ai-summary", json=dashboard_payload())
    second = client.post(
        "/api/dashboard/ai-summary",
        json=dashboard_payload(days="7", ignored_ui_field="不会影响指纹"),
    )

    assert first.status_code == 200
    assert first.json()["cached"] is False
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["summary"] == first.json()["summary"]
    assert len(calls) == 1
    assert "ignored_ui_field" not in calls[0]
    assert calls[0]["days"] == 7
    assert len(cache_rows(isolated_app)) == 1


def test_relevant_data_change_creates_new_fingerprint(
    client, isolated_app, monkeypatch
):
    from app.api import dashboard

    calls = []

    def fake_model(data):
        calls.append(data)
        return generated_summary(len(calls))

    monkeypatch.setattr(dashboard, "analyze_dashboard_management", fake_model)

    first = client.post("/api/dashboard/ai-summary", json=dashboard_payload())
    changed = client.post(
        "/api/dashboard/ai-summary",
        json=dashboard_payload(total_risks=6),
    )

    assert first.json()["cached"] is False
    assert changed.json()["cached"] is False
    assert first.json()["summary"] != changed.json()["summary"]
    assert len(calls) == 2
    rows = cache_rows(isolated_app)
    assert len(rows) == 2
    assert len({row.fingerprint for row in rows}) == 2


def test_corrupt_cache_is_invalidated_and_regenerated(
    client, isolated_app, monkeypatch
):
    from app.api import dashboard
    from app.models import DashboardAICache

    payload = dashboard_payload()
    fingerprint = dashboard.dashboard_ai_fingerprint(payload)
    session = isolated_app["session_factory"]()
    try:
        session.add(
            DashboardAICache(
                fingerprint=fingerprint,
                days=7,
                summary="{损坏的JSON",
            )
        )
        session.commit()
    finally:
        session.close()

    monkeypatch.setattr(
        dashboard,
        "analyze_dashboard_management",
        lambda _data: generated_summary(1),
    )

    response = client.post("/api/dashboard/ai-summary", json=payload)

    assert response.status_code == 200
    assert response.json()["cached"] is False
    rows = cache_rows(isolated_app)
    assert len(rows) == 1
    assert json.loads(rows[0].summary) == generated_summary(1)


def test_model_failure_does_not_write_cache(client, isolated_app, monkeypatch):
    from app.api import dashboard

    def fail_model(_data):
        raise TimeoutError("simulated provider timeout")

    monkeypatch.setattr(dashboard, "analyze_dashboard_management", fail_model)

    response = client.post("/api/dashboard/ai-summary", json=dashboard_payload())

    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "AI_TIMEOUT"
    assert cache_rows(isolated_app) == []


def test_non_object_model_result_does_not_write_cache(
    client, isolated_app, monkeypatch
):
    from app.api import dashboard

    monkeypatch.setattr(
        dashboard,
        "analyze_dashboard_management",
        lambda _data: ["invalid summary"],
    )

    response = client.post("/api/dashboard/ai-summary", json=dashboard_payload())

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "AI_INVALID_RESPONSE"
    assert cache_rows(isolated_app) == []
