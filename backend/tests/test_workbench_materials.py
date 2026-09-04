import json


def _seed_material_workspace(isolated_app):
    from app.models import (
        BidFile,
        BidWorkspace,
        OutlineSection,
        ScoringCriterion,
        SourceReference,
        WorkspaceRevision,
    )

    db = isolated_app["session_factory"]()
    try:
        bid_file = BidFile(
            filename="materials.pdf",
            filepath="uploads/materials.pdf",
            project_name="材料测试项目",
            status="completed",
        )
        db.add(bid_file)
        db.flush()
        workspace = BidWorkspace(bid_file_id=bid_file.id, title="材料测试项目")
        db.add(workspace)
        db.flush()
        source = SourceReference(
            bid_file_id=bid_file.id,
            page=1,
            quote="评分标准原文",
            locator='{"page": 1}',
            fingerprint=f"material-source-{workspace.id}",
        )
        db.add(source)
        db.flush()
        confirmed_section = OutlineSection(
            workspace_id=workspace.id,
            stable_key="confirmed-section",
            title="技术方案",
            sort_order=0,
            origin="user",
            review_status="confirmed",
            source_ref_id=source.id,
        )
        suggested_section = OutlineSection(
            workspace_id=workspace.id,
            stable_key="suggested-section",
            title="待确认章节",
            sort_order=1,
            origin="ai",
            review_status="suggested",
            source_ref_id=source.id,
        )
        confirmed_criterion = ScoringCriterion(
            workspace_id=workspace.id,
            stable_key="confirmed-criterion",
            title="技术评分",
            requirement="提供技术方案",
            max_score=10,
            review_status="confirmed",
            source_ref_id=source.id,
        )
        suggested_criterion = ScoringCriterion(
            workspace_id=workspace.id,
            stable_key="suggested-criterion",
            title="待确认评分点",
            requirement="待确认",
            review_status="suggested",
            source_ref_id=source.id,
        )
        db.add_all([confirmed_section, suggested_section, confirmed_criterion, suggested_criterion])
        db.flush()
        db.add(
            WorkspaceRevision(
                workspace_id=workspace.id,
                revision=1,
                action="create",
                snapshot=json.dumps({"sections": [], "criteria": [], "mappings": [], "materials": []}),
            )
        )
        db.commit()
        return {
            "workspace_id": workspace.id,
            "confirmed_section_id": confirmed_section.id,
            "suggested_section_id": suggested_section.id,
            "confirmed_criterion_id": confirmed_criterion.id,
            "suggested_criterion_id": suggested_criterion.id,
        }
    finally:
        db.close()


def test_material_create_list_update_and_revision_snapshot(client, isolated_app):
    from app.models import ResponseMaterial, WorkspaceRevision

    seeded = _seed_material_workspace(isolated_app)
    workspace_id = seeded["workspace_id"]
    created = client.post(
        f"/api/workspaces/{workspace_id}/materials",
        json={
            "revision": 1,
            "title": " 营业执照复印件 ",
            "criterion_id": seeded["confirmed_criterion_id"],
            "section_id": seeded["confirmed_section_id"],
            "owner_name": " 张三 ",
            "notes": " 加盖公章 ",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["revision"] == 2
    assert body["material_summary"] == {
        "pending": 1,
        "in_progress": 0,
        "completed": 0,
        "blocked": 0,
    }
    material = body["materials"][0]
    assert material["title"] == "营业执照复印件"
    assert material["owner_name"] == "张三"
    assert material["notes"] == "加盖公章"

    listed = client.get(f"/api/workspaces/{workspace_id}/materials")
    assert listed.status_code == 200
    assert listed.json()["items"] == [material]
    assert listed.json()["revision"] == 2

    updated = client.patch(
        f"/api/workspaces/{workspace_id}/materials/{material['id']}",
        json={"revision": 2, "material_status": "completed", "owner_name": None, "notes": " 已核验 "},
    )
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["revision"] == 3
    assert updated_body["material_summary"]["completed"] == 1
    assert updated_body["materials"][0]["owner_name"] is None
    assert updated_body["materials"][0]["notes"] == "已核验"

    db = isolated_app["session_factory"]()
    try:
        assert db.query(ResponseMaterial).count() == 1
        latest = db.query(WorkspaceRevision).filter_by(revision=3).one()
        assert latest.action == "material_update"
        assert json.loads(latest.snapshot)["materials"][0]["material_status"] == "completed"
    finally:
        db.close()


def test_material_validation_and_stale_revision_leave_no_partial_changes(client, isolated_app):
    from app.models import ResponseMaterial, WorkspaceRevision

    seeded = _seed_material_workspace(isolated_app)
    foreign = _seed_material_workspace(isolated_app)
    workspace_id = seeded["workspace_id"]
    cases = [
        ({"revision": 1, "title": "无关联"}, 422, "MATERIAL_TARGET_REQUIRED"),
        ({"revision": 1, "title": "跨工作台", "criterion_id": foreign["confirmed_criterion_id"]}, 422, "MATERIAL_CRITERION_INVALID"),
        ({"revision": 1, "title": "待确认评分点", "criterion_id": seeded["suggested_criterion_id"]}, 409, "MATERIAL_CRITERION_UNCONFIRMED"),
        ({"revision": 1, "title": "待确认章节", "section_id": seeded["suggested_section_id"]}, 409, "MATERIAL_SECTION_UNCONFIRMED"),
    ]
    for payload, status, code in cases:
        response = client.post(f"/api/workspaces/{workspace_id}/materials", json=payload)
        assert response.status_code == status
        assert response.json()["detail"]["code"] == code

    created = client.post(
        f"/api/workspaces/{workspace_id}/materials",
        json={"revision": 1, "title": "证书", "section_id": seeded["confirmed_section_id"]},
    )
    material_id = created.json()["materials"][0]["id"]
    stale = client.patch(
        f"/api/workspaces/{workspace_id}/materials/{material_id}",
        json={"revision": 1, "material_status": "blocked"},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "WORKSPACE_REVISION_CONFLICT"
    empty = client.patch(
        f"/api/workspaces/{workspace_id}/materials/{material_id}", json={"revision": 2}
    )
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "MATERIAL_UPDATE_EMPTY"
    null_status = client.patch(
        f"/api/workspaces/{workspace_id}/materials/{material_id}",
        json={"revision": 2, "material_status": None},
    )
    assert null_status.status_code == 422
    assert null_status.json()["detail"]["code"] == "MATERIAL_STATUS_REQUIRED"

    db = isolated_app["session_factory"]()
    try:
        assert db.query(ResponseMaterial).one().material_status == "pending"
        assert db.query(WorkspaceRevision).count() == 3
    finally:
        db.close()
