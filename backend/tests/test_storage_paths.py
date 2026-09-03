from pathlib import Path


def create_record(isolated_app, filename, filepath):
    from app.models import BidFile

    session = isolated_app["session_factory"]()
    try:
        record = BidFile(
            filename=filename,
            filepath=str(filepath),
            project_name="路径安全测试",
            status="completed",
        )
        session.add(record)
        session.commit()
        return record.id
    finally:
        session.close()


def test_history_does_not_publish_path_outside_upload_root(client, isolated_app):
    outside_path = isolated_app["runtime_dir"] / "outside.pdf"
    outside_path.write_bytes(b"outside")
    record_id = create_record(isolated_app, "outside.pdf", outside_path)

    list_item = client.get("/api/files").json()[0]
    detail = client.get(f"/api/files/{record_id}").json()

    assert list_item["filepath"] is None
    assert detail["filepath"] is None
    assert outside_path.read_bytes() == b"outside"


def test_word_preview_blocks_path_outside_upload_root(
    client, isolated_app, monkeypatch
):
    outside_path = isolated_app["runtime_dir"] / "outside.docx"
    outside_path.write_bytes(b"outside")
    record_id = create_record(isolated_app, "outside.docx", outside_path)
    monkeypatch.setattr(
        "app.api.files.ensure_word_preview_pdf",
        lambda _path: (_ for _ in ()).throw(
            AssertionError("Word/WPS must not receive an unsafe stored path")
        ),
    )

    response = client.get(f"/api/files/{record_id}/preview")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "UNSAFE_STORED_PATH"
    assert outside_path.exists()


def test_delete_record_never_deletes_path_outside_upload_root(client, isolated_app):
    outside_path = isolated_app["runtime_dir"] / "outside.pdf"
    outside_path.write_bytes(b"must-remain")
    record_id = create_record(isolated_app, "outside.pdf", outside_path)

    response = client.delete(f"/api/files/{record_id}?delete_original=true")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["original_deleted"] is False
    assert response.json()["file_cleanup_status"] == "unsafe_path"
    assert outside_path.read_bytes() == b"must-remain"
    assert client.get("/api/files").json() == []


def test_delete_record_removes_only_safe_original_and_preview(client, isolated_app):
    upload_root = isolated_app["runtime_dir"] / "uploads"
    source_path = upload_root / "safe.docx"
    preview_path = upload_root / "safe.docx.preview.pdf"
    source_path.write_bytes(b"source")
    preview_path.write_bytes(b"preview")
    record_id = create_record(isolated_app, "safe.docx", source_path)

    response = client.delete(f"/api/files/{record_id}?delete_original=true")

    assert response.status_code == 200
    assert response.json()["original_deleted"] is True
    assert response.json()["file_cleanup_status"] == "deleted"
    assert not source_path.exists()
    assert not preview_path.exists()


def test_public_upload_path_accepts_only_files_under_upload_root(
    isolated_app, monkeypatch
):
    from app.services import storage_paths

    upload_root = isolated_app["runtime_dir"] / "uploads"
    monkeypatch.setattr(storage_paths, "get_upload_dir", lambda: upload_root)

    assert storage_paths.public_upload_path(upload_root / "safe.pdf") == "/uploads/safe.pdf"
    assert storage_paths.public_upload_path(upload_root.parent / "outside.pdf") is None


def test_upload_filename_traversal_is_reduced_to_basename(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: [{"page": 1, "text": "脱敏内容"}],
    )
    monkeypatch.setattr(
        upload,
        "analyze_bid",
        lambda _text: {"project_name": "路径测试", "risk": []},
    )

    response = client.post(
        "/api/upload",
        files={"file": ("../../escaped.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "escaped.pdf"
    stored = list((isolated_app["runtime_dir"] / "uploads").glob("*.pdf"))
    assert len(stored) == 1
    assert stored[0].parent == isolated_app["runtime_dir"] / "uploads"
