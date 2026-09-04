import json


def _create_workspace(client, isolated_app):
    from app.models import BidFile

    db = isolated_app["session_factory"]()
    try:
        record = BidFile(
            filename="criteria.pdf",
            filepath="uploads/criteria.pdf",
            project_name="评分点测试项目",
            status="completed",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        bid_file_id = record.id
    finally:
        db.close()
    (isolated_app["runtime_dir"] / "uploads" / "criteria.pdf").write_bytes(
        b"%PDF-synthetic"
    )
    return client.post("/api/workspaces", json={"bid_file_id": bid_file_id}).json()


def test_scoring_criteria_extraction_persists_only_source_backed_suggestions(
    client, isolated_app, monkeypatch
):
    from app.api import workspaces
    from app.models import ScoringCriterion, SourceReference, WorkspaceRevision

    workspace = _create_workspace(client, isolated_app)
    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [
            {"page": 8, "text": "类似项目业绩每项得2分，最高6分。"},
            {"page": 9, "text": "技术方案内容完整、措施合理。"},
        ],
    )
    monkeypatch.setattr(
        workspaces,
        "generate_scoring_criteria",
        lambda _pages: {
            "criteria": [
                {
                    "title": "类似项目业绩",
                    "requirement": "提供类似项目业绩证明，每项得2分。",
                    "max_score": 6,
                    "page": 8,
                    "quote": "类似项目业绩每项得2分，最高6分",
                },
                {
                    "title": "技术方案",
                    "requirement": "技术方案内容完整、措施合理。",
                    "max_score": None,
                    "page": 9,
                    "quote": "技术方案内容完整、措施合理",
                },
                {
                    "title": "虚构评分点",
                    "requirement": "不存在",
                    "max_score": 10,
                    "page": 9,
                    "quote": "原文没有这句话",
                },
            ]
        },
    )

    response = client.post(
        f"/api/workspaces/{workspace['id']}/criteria-extractions",
        json={"revision": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revision"] == 2
    assert body["warnings"] == [
        {"index": 2, "code": "CRITERION_SOURCE_NOT_VERIFIED"}
    ]
    assert [item["title"] for item in body["criteria"]] == [
        "类似项目业绩",
        "技术方案",
    ]
    assert body["criteria"][0]["max_score"] == 6.0
    assert body["criteria"][1]["max_score"] is None
    assert all(item["review_status"] == "suggested" for item in body["criteria"])
    assert len(body["source_references"]) == 2

    refreshed = client.get(f"/api/workspaces/{workspace['id']}").json()
    assert refreshed["criteria"] == body["criteria"]
    assert refreshed["source_references"] == body["source_references"]

    db = isolated_app["session_factory"]()
    try:
        assert db.query(ScoringCriterion).count() == 2
        assert db.query(SourceReference).count() == 2
        revision = db.query(WorkspaceRevision).filter_by(revision=2).one()
        assert revision.action == "criteria_extraction"
        assert len(json.loads(revision.snapshot)["criteria"]) == 2
    finally:
        db.close()


def test_scoring_criteria_invalid_sources_and_provider_failure_are_zero_pollution(
    client, isolated_app, monkeypatch
):
    from app.api import workspaces
    from app.models import ScoringCriterion, SourceReference, WorkspaceRevision
    from app.services.ai_errors import AIResponseFormatError

    workspace = _create_workspace(client, isolated_app)
    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [{"page": 1, "text": "真实评分原文"}],
    )
    results = (
        AIResponseFormatError("invalid provider response with private details"),
        {
            "criteria": [
                {
                    "title": "无来源",
                    "requirement": "虚构要求",
                    "max_score": -1,
                    "page": 1,
                    "quote": "无法命中",
                }
            ]
        },
    )
    for result in results:
        def fake_provider(_pages, value=result):
            if isinstance(value, Exception):
                raise value
            return value

        monkeypatch.setattr(workspaces, "generate_scoring_criteria", fake_provider)
        response = client.post(
            f"/api/workspaces/{workspace['id']}/criteria-extractions",
            json={"revision": 1},
        )
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "AI_INVALID_RESPONSE"
        assert "private details" not in response.text

    current = client.get(f"/api/workspaces/{workspace['id']}").json()
    assert current["revision"] == 1
    assert current["criteria"] == []
    db = isolated_app["session_factory"]()
    try:
        assert db.query(ScoringCriterion).count() == 0
        assert db.query(SourceReference).count() == 0
        assert db.query(WorkspaceRevision).count() == 1
    finally:
        db.close()


def _extract_one_criterion(client, isolated_app, monkeypatch, title="评分建议"):
    from app.api import workspaces

    workspace = _create_workspace(client, isolated_app)
    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [{"page": 3, "text": "响应完整得5分"}],
    )
    monkeypatch.setattr(
        workspaces,
        "generate_scoring_criteria",
        lambda _pages: {
            "criteria": [
                {
                    "title": title,
                    "requirement": "提交完整响应材料",
                    "max_score": 5,
                    "page": 3,
                    "quote": "响应完整得5分",
                }
            ]
        },
    )
    extracted = client.post(
        f"/api/workspaces/{workspace['id']}/criteria-extractions",
        json={"revision": 1},
    ).json()
    return extracted, extracted["criteria"][0]


def test_scoring_criteria_can_be_accepted_and_rejected_with_audit_preserved(
    client, isolated_app, monkeypatch
):
    from app.models import ScoringCriterion, SourceReference, WorkspaceRevision

    accepted_workspace, accepted_criterion = _extract_one_criterion(
        client, isolated_app, monkeypatch, "接受评分点"
    )
    accepted = client.post(
        f"/api/workspaces/{accepted_workspace['id']}/criteria/{accepted_criterion['id']}/review",
        json={"decision": "accept", "revision": 2},
    )
    assert accepted.status_code == 200
    assert accepted.json()["revision"] == 3
    assert accepted.json()["criteria"][0]["review_status"] == "confirmed"
    assert len(accepted.json()["source_references"]) == 1

    db = isolated_app["session_factory"]()
    try:
        from app.models import BidFile, BidWorkspace

        second_file = BidFile(
            filename="criteria-second.pdf",
            filepath="uploads/criteria-second.pdf",
            project_name="第二评分项目",
            status="completed",
        )
        db.add(second_file)
        db.commit()
        db.refresh(second_file)
        second_workspace = BidWorkspace(
            bid_file_id=second_file.id,
            title="第二评分项目",
        )
        db.add(second_workspace)
        db.flush()
        db.add(
            WorkspaceRevision(
                workspace_id=second_workspace.id,
                revision=1,
                action="create",
                snapshot=json.dumps(
                    {"sections": [], "criteria": [], "mappings": []},
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        second_workspace_id = second_workspace.id
    finally:
        db.close()
    (isolated_app["runtime_dir"] / "uploads" / "criteria-second.pdf").write_bytes(
        b"%PDF-synthetic"
    )
    rejected_extraction = client.post(
        f"/api/workspaces/{second_workspace_id}/criteria-extractions",
        json={"revision": 1},
    ).json()
    rejected_criterion = rejected_extraction["criteria"][0]
    rejected = client.post(
        f"/api/workspaces/{second_workspace_id}/criteria/{rejected_criterion['id']}/review",
        json={"decision": "reject", "revision": 2},
    )
    assert rejected.status_code == 200
    assert rejected.json()["criteria"][0]["review_status"] == "rejected"
    assert len(rejected.json()["source_references"]) == 1

    db = isolated_app["session_factory"]()
    try:
        assert db.query(ScoringCriterion).count() == 2
        assert db.query(SourceReference).count() == 2
        revisions = db.query(WorkspaceRevision).all()
        actions = [item.action for item in revisions]
        assert "criterion_suggestion_accept" in actions
        assert "criterion_suggestion_reject" in actions
        review_snapshots = {
            item.action: json.loads(item.snapshot)["criteria"][0]["review_status"]
            for item in revisions
            if item.action.startswith("criterion_suggestion_")
        }
        assert review_snapshots == {
            "criterion_suggestion_accept": "confirmed",
            "criterion_suggestion_reject": "rejected",
        }
    finally:
        db.close()


def test_scoring_criterion_review_rejects_stale_repeated_and_cross_workspace(
    client, isolated_app, monkeypatch
):
    extracted, criterion = _extract_one_criterion(client, isolated_app, monkeypatch)
    workspace_id = extracted["id"]
    stale = client.post(
        f"/api/workspaces/{workspace_id}/criteria/{criterion['id']}/review",
        json={"decision": "accept", "revision": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "WORKSPACE_REVISION_CONFLICT"

    accepted = client.post(
        f"/api/workspaces/{workspace_id}/criteria/{criterion['id']}/review",
        json={"decision": "accept", "revision": 2},
    )
    assert accepted.status_code == 200
    repeated = client.post(
        f"/api/workspaces/{workspace_id}/criteria/{criterion['id']}/review",
        json={"decision": "reject", "revision": 3},
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"]["code"] == "CRITERION_REVIEW_NOT_PENDING"

    db = isolated_app["session_factory"]()
    try:
        from app.models import BidFile, BidWorkspace, WorkspaceRevision

        other_file = BidFile(
            filename="other-criteria.pdf",
            filepath="uploads/other-criteria.pdf",
            status="completed",
        )
        db.add(other_file)
        db.commit()
        db.refresh(other_file)
        other_workspace = BidWorkspace(bid_file_id=other_file.id, title="其他工作台")
        db.add(other_workspace)
        db.flush()
        db.add(
            WorkspaceRevision(
                workspace_id=other_workspace.id,
                revision=1,
                action="create",
                snapshot=json.dumps(
                    {"sections": [], "criteria": [], "mappings": []},
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        other_workspace_id = other_workspace.id
    finally:
        db.close()
    cross_workspace = client.post(
        f"/api/workspaces/{other_workspace_id}/criteria/{criterion['id']}/review",
        json={"decision": "reject", "revision": 1},
    )
    assert cross_workspace.status_code == 404
    assert cross_workspace.json()["detail"]["code"] == "CRITERION_NOT_FOUND"
    assert client.get(f"/api/workspaces/{workspace_id}").json()["revision"] == 3
