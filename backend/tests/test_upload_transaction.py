def valid_analysis():
    return {
        "project_name": "上传事务测试项目",
        "risk": [{"level": "低风险", "reason": "脱敏测试"}],
    }


def database_count(isolated_app):
    from app.models import BidFile

    session = isolated_app["session_factory"]()
    try:
        return session.query(BidFile).count()
    finally:
        session.close()


def post_fixture(client, filename="transaction-fixture.pdf"):
    return client.post(
        "/api/upload",
        files={"file": (filename, b"%PDF-isolated-upload", "application/pdf")},
    )


def post_bytes(client, filename, content):
    return client.post(
        "/api/upload",
        files={"file": (filename, content, "application/octet-stream")},
    )


def test_success_keeps_unique_file_and_committed_record(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: [{"page": 1, "text": "脱敏测试内容"}],
    )
    monkeypatch.setattr(upload, "analyze_bid", lambda _text: valid_analysis())

    first = post_fixture(client, "same-name.pdf")
    second = post_fixture(client, "same-name.pdf")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["filename"] == "same-name.pdf"
    assert second.json()["filename"] == "same-name.pdf"
    assert first.json()["filepath"] != second.json()["filepath"]
    stored_files = list((isolated_app["runtime_dir"] / "uploads").iterdir())
    assert len(stored_files) == 2
    assert all(path.read_bytes() == b"%PDF-isolated-upload" for path in stored_files)
    assert database_count(isolated_app) == 2
    listed_paths = {item["filepath"] for item in client.get("/api/files").json()}
    assert listed_paths == {first.json()["filepath"], second.json()["filepath"]}


def test_word_upload_promotes_original_and_preview_together(
    client, isolated_app, monkeypatch
):
    from app.api import upload
    from app.services.word_preview import get_word_preview_path

    def parse_word(filepath):
        get_word_preview_path(filepath).write_bytes(b"rendered-pdf")
        return [{"page": 1, "text": "Word 版式分页内容"}]

    monkeypatch.setattr(upload, "parse_document", parse_word)
    monkeypatch.setattr(upload, "analyze_bid", lambda _text: valid_analysis())

    response = client.post(
        "/api/upload",
        files={
            "file": (
                "layout.docx",
                b"PK\x03\x04isolated-docx-content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    stored_files = list((isolated_app["runtime_dir"] / "uploads").iterdir())
    originals = [path for path in stored_files if path.suffix == ".docx"]
    previews = [path for path in stored_files if path.name.endswith(".docx.preview.pdf")]
    assert len(originals) == 1
    assert len(previews) == 1
    assert originals[0].read_bytes() == b"PK\x03\x04isolated-docx-content"
    assert previews[0].read_bytes() == b"rendered-pdf"
    assert database_count(isolated_app) == 1


def test_partial_write_failure_cleans_file_and_database(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    def fail_during_copy(_source, destination, _max_bytes):
        destination.write(b"partial")
        raise OSError("simulated write failure")

    monkeypatch.setattr(upload, "copy_upload_with_limit", fail_during_copy)

    response = post_fixture(client)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "UPLOAD_PROCESSING_ERROR"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_oversized_upload_is_rejected_before_analysis(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    monkeypatch.setattr(upload, "get_upload_max_bytes", lambda: 8)
    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: (_ for _ in ()).throw(
            AssertionError("parser must not run for an oversized upload")
        ),
    )
    monkeypatch.setattr(
        upload,
        "analyze_bid",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("DeepSeek must not run for an oversized upload")
        ),
    )

    response = post_bytes(client, "oversized.pdf", b"123456789")

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_parse_failure_cleans_file_and_database(client, isolated_app, monkeypatch):
    from app.api import upload

    def fail_parse(_filepath):
        raise ValueError("simulated parse failure")

    monkeypatch.setattr(upload, "parse_document", fail_parse)

    response = post_fixture(client)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "UPLOAD_PROCESSING_ERROR"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_unsupported_upload_is_rejected_before_analysis(client, isolated_app):
    response = post_fixture(client, "unsupported.txt")

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_corrupt_pdf_returns_parse_error_and_leaves_no_state(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    monkeypatch.setattr(
        upload,
        "analyze_bid",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("DeepSeek must not run for a corrupt PDF")
        ),
    )

    response = post_bytes(
        client,
        "corrupt.pdf",
        b"%PDF-1.7\nstructurally-corrupt-content",
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DOCUMENT_PARSE_ERROR"
    assert "PDF" in response.json()["detail"]["message"]
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_corrupt_docx_is_rejected_before_wps_and_leaves_no_state(
    client, isolated_app, monkeypatch
):
    from app.api import upload
    from app.services import parser

    monkeypatch.setattr(
        parser,
        "ensure_word_preview_pdf",
        lambda _path: (_ for _ in ()).throw(
            AssertionError("WPS must not run for a corrupt DOCX")
        ),
    )
    monkeypatch.setattr(
        upload,
        "analyze_bid",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("DeepSeek must not run for a corrupt DOCX")
        ),
    )

    response = post_bytes(client, "corrupt.docx", b"PK\x03\x04not-a-valid-docx")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DOCUMENT_PARSE_ERROR"
    assert "DOCX" in response.json()["detail"]["message"]
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_mime_mismatch_is_rejected_before_parser_and_ai(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: (_ for _ in ()).throw(
            AssertionError("parser must not run for a MIME mismatch")
        ),
    )
    monkeypatch.setattr(
        upload,
        "analyze_bid",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("DeepSeek must not run for a MIME mismatch")
        ),
    )

    response = client.post(
        "/api/upload",
        files={"file": ("renamed.pdf", b"%PDF-test", "image/png")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "FILE_TYPE_MISMATCH"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_signature_mismatch_is_rejected_before_parser_and_ai(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: (_ for _ in ()).throw(
            AssertionError("parser must not run for a signature mismatch")
        ),
    )
    monkeypatch.setattr(
        upload,
        "analyze_bid",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("DeepSeek must not run for a signature mismatch")
        ),
    )

    response = post_bytes(client, "renamed.pdf", b"MZ-not-a-pdf")

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "FILE_SIGNATURE_MISMATCH"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_missing_ocr_configuration_cleans_upload_and_returns_503(
    client, isolated_app, monkeypatch
):
    from app.api import upload
    from app.services.ocr import OCRConfigurationError

    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: (_ for _ in ()).throw(
            OCRConfigurationError("百度 OCR 尚未配置")
        ),
    )

    response = post_fixture(client, "scanned.pdf")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "OCR_NOT_CONFIGURED"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0


def test_commit_failure_cleans_promoted_file_and_rolls_back_record(
    client, isolated_app, monkeypatch
):
    from app.api import upload

    session = isolated_app["session_factory"]()
    monkeypatch.setattr(upload, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        upload,
        "parse_document",
        lambda _filepath: [{"page": 1, "text": "脱敏测试内容"}],
    )
    monkeypatch.setattr(upload, "analyze_bid", lambda _text: valid_analysis())
    monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))

    response = post_fixture(client)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "UPLOAD_PROCESSING_ERROR"
    assert list((isolated_app["runtime_dir"] / "uploads").iterdir()) == []
    assert database_count(isolated_app) == 0
