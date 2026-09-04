import json


def test_workbench_directory_criterion_material_closed_loop(
    client, isolated_app, monkeypatch
):
    from app.api import workspaces
    from app.models import BidFile, WorkspaceRevision

    db = isolated_app["session_factory"]()
    try:
        bid_file = BidFile(
            filename="closed-loop.pdf",
            filepath="uploads/closed-loop.pdf",
            project_name="闭环测试项目",
            status="completed",
        )
        db.add(bid_file)
        db.commit()
        db.refresh(bid_file)
        bid_file_id = bid_file.id
    finally:
        db.close()
    (isolated_app["runtime_dir"] / "uploads" / "closed-loop.pdf").write_bytes(
        b"%PDF-synthetic"
    )

    workspace = client.post(
        "/api/workspaces", json={"bid_file_id": bid_file_id}
    ).json()
    workspace_id = workspace["id"]
    section_response = client.post(
        f"/api/workspaces/{workspace_id}/sections",
        json={"revision": 1, "title": "技术响应方案"},
    )
    assert section_response.status_code == 200
    section = section_response.json()["sections"][0]

    monkeypatch.setattr(
        workspaces,
        "parse_document",
        lambda _path: [{"page": 6, "text": "技术方案完整可行得10分"}],
    )
    monkeypatch.setattr(
        workspaces,
        "generate_scoring_criteria",
        lambda _pages: {
            "criteria": [
                {
                    "title": "技术方案完整性",
                    "requirement": "提交完整可行的技术方案",
                    "max_score": 10,
                    "page": 6,
                    "quote": "技术方案完整可行得10分",
                }
            ]
        },
    )
    extracted = client.post(
        f"/api/workspaces/{workspace_id}/criteria-extractions",
        json={"revision": 2},
    )
    assert extracted.status_code == 200
    criterion = extracted.json()["criteria"][0]
    source = extracted.json()["source_references"][0]
    assert source["page"] == 6
    assert source["quote"] == "技术方案完整可行得10分"

    reviewed = client.post(
        f"/api/workspaces/{workspace_id}/criteria/{criterion['id']}/review",
        json={"revision": 3, "decision": "accept"},
    )
    assert reviewed.status_code == 200
    mapped = client.put(
        f"/api/workspaces/{workspace_id}/mappings",
        json={
            "revision": 4,
            "mappings": [
                {
                    "criterion_id": criterion["id"],
                    "section_id": section["id"],
                    "rationale": "技术评分点由技术响应方案覆盖",
                }
            ],
        },
    )
    assert mapped.status_code == 200
    assert mapped.json()["coverage"] == {"confirmed": 1, "gap": 0, "proposed": 0}

    created = client.post(
        f"/api/workspaces/{workspace_id}/materials",
        json={
            "revision": 5,
            "title": "技术方案终稿",
            "criterion_id": criterion["id"],
            "section_id": section["id"],
            "owner_name": "技术负责人",
            "material_status": "in_progress",
        },
    )
    assert created.status_code == 200
    material = created.json()["materials"][0]
    assert created.json()["material_summary"] == {
        "pending": 0,
        "in_progress": 1,
        "completed": 0,
        "blocked": 0,
    }

    completed = client.patch(
        f"/api/workspaces/{workspace_id}/materials/{material['id']}",
        json={"revision": 6, "material_status": "completed", "notes": "人工复核通过"},
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["revision"] == 7
    assert body["coverage"] == {"confirmed": 1, "gap": 0, "proposed": 0}
    assert body["material_summary"] == {
        "pending": 0,
        "in_progress": 0,
        "completed": 1,
        "blocked": 0,
    }
    assert body["source_references"] == [source]
    assert body["criteria"][0]["source_ref_id"] == source["id"]
    assert body["mappings"][0]["criterion_id"] == criterion["id"]
    assert body["materials"][0]["notes"] == "人工复核通过"

    conflict = client.patch(
        f"/api/workspaces/{workspace_id}/materials/{material['id']}",
        json={"revision": 6, "material_status": "blocked"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["current_revision"] == 7

    db = isolated_app["session_factory"]()
    try:
        revisions = (
            db.query(WorkspaceRevision)
            .filter(WorkspaceRevision.workspace_id == workspace_id)
            .order_by(WorkspaceRevision.revision)
            .all()
        )
        assert [item.revision for item in revisions] == list(range(1, 8))
        assert [item.action for item in revisions] == [
            "create",
            "section_create",
            "criteria_extraction",
            "criterion_suggestion_accept",
            "mappings_upsert",
            "material_create",
            "material_update",
        ]
        final_snapshot = json.loads(revisions[-1].snapshot)
        assert final_snapshot["criteria"][0]["review_status"] == "confirmed"
        assert final_snapshot["mappings"][0]["coverage_status"] == "confirmed"
        assert final_snapshot["materials"][0]["material_status"] == "completed"
    finally:
        db.close()
