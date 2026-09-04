import json


def _create_bid_file(session_factory):
    from app.models import BidFile

    db = session_factory()
    try:
        record = BidFile(
            filename="authorized-sample.pdf",
            filepath="uploads/authorized-sample.pdf",
            project_name="示例项目",
            status="completed",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.id
    finally:
        db.close()


def test_create_workspace_is_idempotent_and_creates_initial_revision(client, isolated_app):
    from app.models import BidWorkspace, WorkspaceRevision

    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    first = client.post("/api/workspaces", json={"bid_file_id": bid_file_id})
    second = client.post("/api/workspaces", json={"bid_file_id": bid_file_id, "title": "不会覆盖"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["title"] == "示例项目"
    assert first.json()["revision"] == 1
    assert first.json()["sections"] == []

    db = isolated_app["session_factory"]()
    try:
        assert db.query(BidWorkspace).count() == 1
        revision = db.query(WorkspaceRevision).one()
        assert revision.action == "create"
        assert revision.revision == 1
    finally:
        db.close()


def test_get_workspace_and_missing_resources_have_stable_contract(client, isolated_app):
    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    created = client.post(
        "/api/workspaces",
        json={"bid_file_id": bid_file_id, "title": "  人工工作台  "},
    )
    workspace_id = created.json()["id"]

    response = client.get(f"/api/workspaces/{workspace_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "人工工作台"
    assert response.json()["coverage"] == {"confirmed": 0, "gap": 0, "proposed": 0}

    missing_workspace = client.get("/api/workspaces/999999")
    assert missing_workspace.status_code == 404
    assert missing_workspace.json()["detail"]["code"] == "WORKSPACE_NOT_FOUND"

    missing_file = client.post("/api/workspaces", json={"bid_file_id": 999999})
    assert missing_file.status_code == 404
    assert missing_file.json()["detail"]["code"] == "BID_FILE_NOT_FOUND"


def test_manual_sections_can_be_created_renamed_and_reordered(client, isolated_app):
    from app.models import WorkspaceRevision

    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    workspace = client.post("/api/workspaces", json={"bid_file_id": bid_file_id}).json()
    workspace_id = workspace["id"]

    first = client.post(
        f"/api/workspaces/{workspace_id}/sections",
        json={"title": " 第一章 ", "revision": 1},
    )
    second = client.post(
        f"/api/workspaces/{workspace_id}/sections",
        json={"title": "第二章", "revision": 2},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["revision"] == 3
    assert [(item["title"], item["sort_order"]) for item in second.json()["sections"]] == [
        ("第一章", 0),
        ("第二章", 1),
    ]
    first_id = second.json()["sections"][0]["id"]
    updated = client.patch(
        f"/api/workspaces/{workspace_id}/sections/{first_id}",
        json={"title": "资格审查", "sort_order": 1, "revision": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 4
    assert [(item["title"], item["sort_order"]) for item in updated.json()["sections"]] == [
        ("第二章", 0),
        ("资格审查", 1),
    ]
    assert all(item["origin"] == "user" for item in updated.json()["sections"])
    assert all(item["review_status"] == "confirmed" for item in updated.json()["sections"])

    db = isolated_app["session_factory"]()
    try:
        revisions = db.query(WorkspaceRevision).order_by(WorkspaceRevision.revision).all()
        assert [item.revision for item in revisions] == [1, 2, 3, 4]
        assert json.loads(revisions[-1].snapshot)["sections"][1]["title"] == "资格审查"
    finally:
        db.close()


def test_section_updates_reject_stale_revision_without_partial_write(client, isolated_app):
    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    workspace = client.post("/api/workspaces", json={"bid_file_id": bid_file_id}).json()
    workspace_id = workspace["id"]
    created = client.post(
        f"/api/workspaces/{workspace_id}/sections",
        json={"title": "技术部分", "revision": 1},
    ).json()
    section_id = created["sections"][0]["id"]

    conflict = client.patch(
        f"/api/workspaces/{workspace_id}/sections/{section_id}",
        json={"title": "不应写入", "revision": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == {
        "code": "WORKSPACE_REVISION_CONFLICT",
        "message": "工作台已被更新，请重新加载后再试。",
        "current_revision": 2,
    }
    current = client.get(f"/api/workspaces/{workspace_id}").json()
    assert current["revision"] == 2
    assert current["sections"][0]["title"] == "技术部分"


def test_section_parent_and_cross_workspace_ids_are_rejected(client, isolated_app):
    first_file = _create_bid_file(isolated_app["session_factory"])
    first_workspace = client.post("/api/workspaces", json={"bid_file_id": first_file}).json()

    db = isolated_app["session_factory"]()
    try:
        from app.models import BidFile

        other_file = BidFile(filename="other.pdf", filepath="uploads/other.pdf", status="completed")
        db.add(other_file)
        db.commit()
        db.refresh(other_file)
        other_file_id = other_file.id
    finally:
        db.close()
    second_workspace = client.post("/api/workspaces", json={"bid_file_id": other_file_id}).json()
    foreign_section = client.post(
        f"/api/workspaces/{second_workspace['id']}/sections",
        json={"title": "其他工作台章节", "revision": 1},
    ).json()["sections"][0]

    invalid_parent = client.post(
        f"/api/workspaces/{first_workspace['id']}/sections",
        json={"title": "错误子章节", "parent_id": foreign_section["id"], "revision": 1},
    )
    assert invalid_parent.status_code == 422
    assert invalid_parent.json()["detail"]["code"] == "SECTION_PARENT_INVALID"
    wrong_workspace = client.patch(
        f"/api/workspaces/{first_workspace['id']}/sections/{foreign_section['id']}",
        json={"title": "不应修改", "revision": 1},
    )
    assert wrong_workspace.status_code == 404
    assert wrong_workspace.json()["detail"]["code"] == "SECTION_NOT_FOUND"


def test_ai_outline_suggestions_require_verified_sources_and_remain_unconfirmed(
    client, isolated_app, monkeypatch
):
    from app.api import workspaces
    from app.models import OutlineSection, SourceReference, WorkspaceRevision

    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    source_path = isolated_app["runtime_dir"] / "uploads" / "authorized-sample.pdf"
    source_path.write_bytes(b"%PDF-synthetic")
    workspace = client.post("/api/workspaces", json={"bid_file_id": bid_file_id}).json()
    workspace_id = workspace["id"]
    client.post(
        f"/api/workspaces/{workspace_id}/sections",
        json={"title": "人工确认章节", "revision": 1},
    )
    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [
            {"page": 1, "text": "投标文件应包括资格审查资料和技术方案。"},
            {"page": 2, "text": "施工组织设计应说明质量保证措施。"},
        ],
    )
    monkeypatch.setattr(
        workspaces,
        "generate_outline_suggestions",
        lambda _pages: {
            "suggestions": [
                {"title": "资格审查", "parent_index": None, "page": 1, "quote": "资格审查资料"},
                {"title": "施工组织设计", "parent_index": None, "page": 2, "quote": "施工组织设计"},
                {"title": "质量保证措施", "parent_index": 1, "page": 2, "quote": "质量保证措施"},
                {"title": "虚构章节", "parent_index": None, "page": 2, "quote": "原文不存在"},
            ]
        },
    )

    response = client.post(
        f"/api/workspaces/{workspace_id}/outline-suggestions",
        json={"revision": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revision"] == 3
    assert body["warnings"] == [{"index": 3, "code": "SOURCE_NOT_VERIFIED"}]
    assert body["sections"][0]["title"] == "人工确认章节"
    ai_sections = [item for item in body["sections"] if item["origin"] == "ai"]
    assert len(ai_sections) == 3
    assert all(item["review_status"] == "suggested" for item in ai_sections)
    assert ai_sections[0]["sort_order"] == 1
    assert ai_sections[2]["parent_id"] == ai_sections[1]["id"]
    assert len(body["source_references"]) == 3
    assert body["source_references"][0]["quote"] == "资格审查资料"
    assert body["source_references"][0]["locator"] == {"page": 1}

    db = isolated_app["session_factory"]()
    try:
        assert db.query(OutlineSection).count() == 4
        assert db.query(SourceReference).count() == 3
        revision = db.query(WorkspaceRevision).filter_by(revision=3).one()
        assert revision.action == "outline_suggestions"
        assert len(json.loads(revision.snapshot)["sections"]) == 4
    finally:
        db.close()


def test_ai_outline_failure_and_unverified_response_leave_no_partial_revision(
    client, isolated_app, monkeypatch
):
    from app.api import workspaces
    from app.models import OutlineSection, SourceReference, WorkspaceRevision
    from app.services.ai_errors import AIResponseFormatError

    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    (isolated_app["runtime_dir"] / "uploads" / "authorized-sample.pdf").write_bytes(
        b"%PDF-synthetic"
    )
    workspace = client.post("/api/workspaces", json={"bid_file_id": bid_file_id}).json()
    workspace_id = workspace["id"]
    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [{"page": 1, "text": "真实原文"}],
    )

    for provider_result in (
        AIResponseFormatError("provider response contains secret details"),
        {"suggestions": [{"title": "虚构", "parent_index": None, "page": 1, "quote": "不存在"}]},
    ):
        def fake_provider(_pages, value=provider_result):
            if isinstance(value, Exception):
                raise value
            return value

        monkeypatch.setattr(workspaces, "generate_outline_suggestions", fake_provider)
        response = client.post(
            f"/api/workspaces/{workspace_id}/outline-suggestions",
            json={"revision": 1},
        )
        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "AI_INVALID_RESPONSE"
        assert "secret details" not in response.text

    current = client.get(f"/api/workspaces/{workspace_id}").json()
    assert current["revision"] == 1
    db = isolated_app["session_factory"]()
    try:
        assert db.query(OutlineSection).count() == 0
        assert db.query(SourceReference).count() == 0
        assert db.query(WorkspaceRevision).count() == 1
    finally:
        db.close()


def _create_ai_suggestion(client, isolated_app, monkeypatch, title="AI建议"):
    from app.api import workspaces

    bid_file_id = _create_bid_file(isolated_app["session_factory"])
    (isolated_app["runtime_dir"] / "uploads" / "authorized-sample.pdf").write_bytes(
        b"%PDF-synthetic"
    )
    workspace = client.post("/api/workspaces", json={"bid_file_id": bid_file_id}).json()
    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [{"page": 1, "text": "资格审查标准"}],
    )
    monkeypatch.setattr(
        workspaces,
        "generate_outline_suggestions",
        lambda _pages: {
            "suggestions": [
                {
                    "title": title,
                    "parent_index": None,
                    "page": 1,
                    "quote": "资格审查标准",
                }
            ]
        },
    )
    generated = client.post(
        f"/api/workspaces/{workspace['id']}/outline-suggestions",
        json={"revision": 1},
    ).json()
    return generated, generated["sections"][0]


def test_ai_suggestions_can_be_accepted_or_rejected_without_losing_audit_data(
    client, isolated_app, monkeypatch
):
    from app.models import OutlineSection, SourceReference, WorkspaceRevision

    accepted_workspace, accepted_section = _create_ai_suggestion(
        client, isolated_app, monkeypatch, "接受建议"
    )
    accepted = client.post(
        f"/api/workspaces/{accepted_workspace['id']}/sections/{accepted_section['id']}/review",
        json={"decision": "accept", "revision": 2},
    )
    assert accepted.status_code == 200
    assert accepted.json()["revision"] == 3
    assert accepted.json()["sections"][0]["review_status"] == "confirmed"
    assert accepted.json()["sections"][0]["origin"] == "ai"
    assert len(accepted.json()["source_references"]) == 1

    db = isolated_app["session_factory"]()
    try:
        from app.models import BidFile

        second_file = BidFile(
            filename="second.pdf",
            filepath="uploads/second.pdf",
            project_name="第二项目",
            status="completed",
        )
        db.add(second_file)
        db.commit()
        db.refresh(second_file)
        second_file_id = second_file.id
    finally:
        db.close()
    (isolated_app["runtime_dir"] / "uploads" / "second.pdf").write_bytes(
        b"%PDF-synthetic"
    )
    second_workspace = client.post(
        "/api/workspaces", json={"bid_file_id": second_file_id}
    ).json()
    from app.api import workspaces

    monkeypatch.setattr(
        workspaces,
        "generate_outline_suggestions",
        lambda _pages: {
            "suggestions": [
                {
                    "title": "拒绝建议",
                    "parent_index": None,
                    "page": 1,
                    "quote": "资格审查标准",
                }
            ]
        },
    )
    rejected_generated = client.post(
        f"/api/workspaces/{second_workspace['id']}/outline-suggestions",
        json={"revision": 1},
    ).json()
    rejected_section = rejected_generated["sections"][0]
    rejected = client.post(
        f"/api/workspaces/{second_workspace['id']}/sections/{rejected_section['id']}/review",
        json={"decision": "reject", "revision": 2},
    )
    assert rejected.status_code == 200
    assert rejected.json()["sections"][0]["review_status"] == "rejected"
    assert len(rejected.json()["source_references"]) == 1

    db = isolated_app["session_factory"]()
    try:
        assert db.query(OutlineSection).count() == 2
        assert db.query(SourceReference).count() == 2
        actions = [item.action for item in db.query(WorkspaceRevision).all()]
        assert "section_suggestion_accept" in actions
        assert "section_suggestion_reject" in actions
    finally:
        db.close()


def test_suggestion_review_rejects_stale_manual_and_already_reviewed_sections(
    client, isolated_app, monkeypatch
):
    generated, suggestion = _create_ai_suggestion(client, isolated_app, monkeypatch)
    workspace_id = generated["id"]
    stale = client.post(
        f"/api/workspaces/{workspace_id}/sections/{suggestion['id']}/review",
        json={"decision": "accept", "revision": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "WORKSPACE_REVISION_CONFLICT"

    accepted = client.post(
        f"/api/workspaces/{workspace_id}/sections/{suggestion['id']}/review",
        json={"decision": "accept", "revision": 2},
    )
    assert accepted.status_code == 200
    repeated = client.post(
        f"/api/workspaces/{workspace_id}/sections/{suggestion['id']}/review",
        json={"decision": "reject", "revision": 3},
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"]["code"] == "SECTION_REVIEW_NOT_PENDING"
    assert client.get(f"/api/workspaces/{workspace_id}").json()["revision"] == 3

    manual = client.post(
        f"/api/workspaces/{workspace_id}/sections",
        json={"title": "人工章节", "revision": 3},
    ).json()
    assert len(manual["source_references"]) == 1
    manual_section = next(item for item in manual["sections"] if item["origin"] == "user")
    manual_review = client.post(
        f"/api/workspaces/{workspace_id}/sections/{manual_section['id']}/review",
        json={"decision": "reject", "revision": 4},
    )
    assert manual_review.status_code == 409
    assert manual_review.json()["detail"]["code"] == "SECTION_REVIEW_NOT_PENDING"
    assert client.get(f"/api/workspaces/{workspace_id}").json()["revision"] == 4
