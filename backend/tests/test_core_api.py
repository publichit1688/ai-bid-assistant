import json
from pathlib import Path

from sqlalchemy import text


def test_database_is_isolated_from_user_workspace(isolated_app):
    runtime_dir = isolated_app["runtime_dir"].resolve()

    with isolated_app["engine"].connect() as connection:
        database_rows = connection.execute(text("PRAGMA database_list")).all()

    main_database = next(row[2] for row in database_rows if row[1] == "main")
    assert Path(main_database).resolve() == runtime_dir / "bid.db"
    assert runtime_dir not in Path(__file__).resolve().parents


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello AI Bid Assistant"}


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Bid Assistant",
    }


def test_readiness_endpoint_reports_database_and_storage(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "AI Bid Assistant",
        "checks": {
            "database": "ok",
            "upload_storage": "ok",
            "report_storage": "ok",
            "auth_configuration": "ok",
        },
    }


def test_readiness_endpoint_returns_503_for_dependency_failure(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.health.readiness_report",
        lambda: {
            "status": "degraded",
            "service": "AI Bid Assistant",
            "checks": {
                "database": "error",
                "upload_storage": "ok",
                "report_storage": "ok",
                "auth_configuration": "ok",
            },
        },
    )

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "error"


def test_files_endpoint_uses_only_isolated_fixture_data(client, isolated_app):
    from app.models import BidFile

    session = isolated_app["session_factory"]()
    try:
        session.add(
            BidFile(
                filename="isolated-fixture.pdf",
                filepath="uploads/isolated-fixture.pdf",
                project_name="pytest 隔离项目",
                risk=json.dumps(
                    [
                        {
                            "level": "高风险",
                            "deduction": 20,
                            "reason": "测试风险",
                        }
                    ],
                    ensure_ascii=False,
                ),
                status="analyzed",
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/api/files")

    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    assert files[0]["filename"] == "isolated-fixture.pdf"
    assert files[0]["project_name"] == "pytest 隔离项目"
    assert files[0]["risk_count"] == 1
    assert files[0]["score"] == 80


def test_score_contract_matches_list_detail_and_dashboard(client, isolated_app):
    from app.models import BidFile

    risks = [
        {"level": "高风险", "reason": "涉及保证金"},
        {"level": "中低风险", "deduction": "8"},
        {"level": "低风险", "deduction": -3},
        {"level": None},
        "损坏条目",
    ]
    session = isolated_app["session_factory"]()
    try:
        record = BidFile(
            filename="contract-fixture.pdf",
            filepath="uploads/contract-fixture.pdf",
            project_name="评分契约项目",
            risk=json.dumps(risks, ensure_ascii=False),
            status="completed",
        )
        session.add(record)
        session.commit()
        record_id = record.id
    finally:
        session.close()

    list_item = client.get("/api/files").json()[0]
    detail = client.get(f"/api/files/{record_id}").json()
    dashboard = client.get("/api/dashboard?days=7").json()
    dashboard_item = next(
        item
        for item in dashboard["recent_projects"]
        if item["id"] == record_id
    )

    contract_fields = (
        "score",
        "score_level",
        "risk_count",
        "high_count",
        "middle_count",
        "low_count",
        "total_deduction",
    )
    expected = {field: list_item[field] for field in contract_fields}
    assert expected == {
        "score": 62,
        "score_level": "中风险",
        "risk_count": 4,
        "high_count": 1,
        "middle_count": 1,
        "low_count": 1,
        "total_deduction": 38,
    }
    assert {field: detail[field] for field in contract_fields} == expected
    assert {field: dashboard_item[field] for field in contract_fields} == expected
