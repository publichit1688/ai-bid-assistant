import json


def _seed_mapping_workspace(isolated_app):
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
            filename="mapping.pdf",
            filepath="uploads/mapping.pdf",
            project_name="映射测试项目",
            status="completed",
        )
        db.add(bid_file)
        db.flush()
        workspace = BidWorkspace(bid_file_id=bid_file.id, title="映射测试项目")
        db.add(workspace)
        db.flush()
        source = SourceReference(
            bid_file_id=bid_file.id,
            page=5,
            quote="评分标准原文",
            locator='{"page": 5}',
            fingerprint="mapping-source",
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
            title="技术方案评分",
            requirement="提交技术方案",
            max_score=10,
            review_status="confirmed",
            source_ref_id=source.id,
        )
        gap_criterion = ScoringCriterion(
            workspace_id=workspace.id,
            stable_key="gap-criterion",
            title="业绩评分",
            requirement="提交业绩",
            max_score=5,
            review_status="confirmed",
            source_ref_id=source.id,
        )
        suggested_criterion = ScoringCriterion(
            workspace_id=workspace.id,
            stable_key="suggested-criterion",
            title="待确认评分点",
            requirement="待确认要求",
            max_score=None,
            review_status="suggested",
            source_ref_id=source.id,
        )
        db.add_all(
            [
                confirmed_section,
                suggested_section,
                confirmed_criterion,
                gap_criterion,
                suggested_criterion,
            ]
        )
        db.flush()
        db.add(
            WorkspaceRevision(
                workspace_id=workspace.id,
                revision=1,
                action="create",
                snapshot=json.dumps(
                    {"sections": [], "criteria": [], "mappings": []},
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        return {
            "workspace_id": workspace.id,
            "confirmed_section_id": confirmed_section.id,
            "suggested_section_id": suggested_section.id,
            "confirmed_criterion_id": confirmed_criterion.id,
            "gap_criterion_id": gap_criterion.id,
            "suggested_criterion_id": suggested_criterion.id,
        }
    finally:
        db.close()


def test_confirmed_criteria_map_to_confirmed_sections_with_coverage_and_snapshot(
    client, isolated_app
):
    from app.models import CriterionSectionMapping, WorkspaceRevision

    seeded = _seed_mapping_workspace(isolated_app)
    response = client.put(
        f"/api/workspaces/{seeded['workspace_id']}/mappings",
        json={
            "revision": 1,
            "mappings": [
                {
                    "criterion_id": seeded["confirmed_criterion_id"],
                    "section_id": seeded["confirmed_section_id"],
                    "rationale": " 对应技术方案章节 ",
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revision"] == 2
    assert body["coverage"] == {"confirmed": 1, "gap": 1, "proposed": 1}
    assert body["mappings"] == [
        {
            "id": body["mappings"][0]["id"],
            "criterion_id": seeded["confirmed_criterion_id"],
            "section_id": seeded["confirmed_section_id"],
            "coverage_status": "confirmed",
            "rationale": "对应技术方案章节",
            "origin": "user",
        }
    ]

    updated = client.put(
        f"/api/workspaces/{seeded['workspace_id']}/mappings",
        json={
            "revision": 2,
            "mappings": [
                {
                    "criterion_id": seeded["confirmed_criterion_id"],
                    "section_id": seeded["confirmed_section_id"],
                    "rationale": "更新后的人工说明",
                }
            ],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 3
    assert updated.json()["mappings"][0]["rationale"] == "更新后的人工说明"

    db = isolated_app["session_factory"]()
    try:
        assert db.query(CriterionSectionMapping).count() == 1
        latest = db.query(WorkspaceRevision).filter_by(revision=3).one()
        assert latest.action == "mappings_upsert"
        snapshot = json.loads(latest.snapshot)
        assert snapshot["mappings"][0]["coverage_status"] == "confirmed"
    finally:
        db.close()


def test_mapping_validation_and_stale_revision_do_not_create_partial_rows(
    client, isolated_app
):
    from app.models import CriterionSectionMapping, WorkspaceRevision

    seeded = _seed_mapping_workspace(isolated_app)
    foreign = _seed_mapping_workspace(isolated_app)
    workspace_id = seeded["workspace_id"]
    cases = [
        (
            {
                "criterion_id": seeded["suggested_criterion_id"],
                "section_id": seeded["confirmed_section_id"],
            },
            409,
            "MAPPING_CRITERION_UNCONFIRMED",
        ),
        (
            {
                "criterion_id": seeded["confirmed_criterion_id"],
                "section_id": seeded["suggested_section_id"],
            },
            409,
            "MAPPING_SECTION_UNCONFIRMED",
        ),
        (
            {
                "criterion_id": foreign["confirmed_criterion_id"],
                "section_id": seeded["confirmed_section_id"],
            },
            422,
            "MAPPING_CRITERION_INVALID",
        ),
        (
            {
                "criterion_id": seeded["confirmed_criterion_id"],
                "section_id": foreign["confirmed_section_id"],
            },
            422,
            "MAPPING_SECTION_INVALID",
        ),
    ]
    for mapping, status, code in cases:
        response = client.put(
            f"/api/workspaces/{workspace_id}/mappings",
            json={"revision": 1, "mappings": [mapping]},
        )
        assert response.status_code == status
        assert response.json()["detail"]["code"] == code

    duplicate = client.put(
        f"/api/workspaces/{workspace_id}/mappings",
        json={
            "revision": 1,
            "mappings": [
                {
                    "criterion_id": seeded["confirmed_criterion_id"],
                    "section_id": seeded["confirmed_section_id"],
                },
                {
                    "criterion_id": seeded["confirmed_criterion_id"],
                    "section_id": seeded["confirmed_section_id"],
                },
            ],
        },
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["detail"]["code"] == "MAPPING_DUPLICATE"

    created = client.put(
        f"/api/workspaces/{workspace_id}/mappings",
        json={
            "revision": 1,
            "mappings": [
                {
                    "criterion_id": seeded["confirmed_criterion_id"],
                    "section_id": seeded["confirmed_section_id"],
                }
            ],
        },
    )
    assert created.status_code == 200
    stale = client.put(
        f"/api/workspaces/{workspace_id}/mappings",
        json={
            "revision": 1,
            "mappings": [
                {
                    "criterion_id": seeded["gap_criterion_id"],
                    "section_id": seeded["confirmed_section_id"],
                }
            ],
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "WORKSPACE_REVISION_CONFLICT"

    current = client.get(f"/api/workspaces/{workspace_id}").json()
    assert current["revision"] == 2
    assert len(current["mappings"]) == 1
    db = isolated_app["session_factory"]()
    try:
        assert db.query(CriterionSectionMapping).count() == 1
        assert db.query(WorkspaceRevision).count() == 3
    finally:
        db.close()
