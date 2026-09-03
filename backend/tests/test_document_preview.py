from docx import Document
import fitz
import json
import struct


def create_docx(path, paragraphs):
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(path)


def create_pdf(path, page_count=1):
    document = fitz.open()
    for page_number in range(1, page_count + 1):
        page = document.new_page()
        page.insert_text((72, 72), f"preview page {page_number}")
    document.save(path)
    document.close()


def test_docx_preview_returns_rendered_pdf_pages(client, isolated_app, monkeypatch):
    from app.models import BidFile

    source_path = isolated_app["runtime_dir"] / "uploads" / "preview.docx"
    preview_path = isolated_app["runtime_dir"] / "uploads" / "preview.docx.preview.pdf"
    create_docx(source_path, ["第一段招标要求", "第二段风险内容"])
    create_pdf(preview_path, page_count=2)
    monkeypatch.setattr(
        "app.api.files.ensure_word_preview_pdf",
        lambda path: preview_path,
    )

    session = isolated_app["session_factory"]()
    try:
        record = BidFile(
            filename="preview.docx",
            filepath=str(source_path),
            risk=json.dumps(
                [{"page": 1, "highlight_words": ["preview page 2"]}]
            ),
            status="completed",
        )
        session.add(record)
        session.commit()
        record_id = record.id
    finally:
        session.close()

    response = client.get(f"/api/files/{record_id}/preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "pdf"
    assert payload["source_format"] == "docx"
    assert payload["pagination"] == "rendered"
    assert payload["filepath"] == "/uploads/preview.docx.preview.pdf"
    assert payload["num_pages"] == 2
    assert payload["renderer"] == "unknown"
    assert payload["risk_page_map"] == {"0": 2}


def test_pdf_does_not_use_docx_text_preview(client, isolated_app):
    from app.models import BidFile

    source_path = isolated_app["runtime_dir"] / "uploads" / "preview.pdf"
    source_path.write_bytes(b"%PDF-placeholder")

    session = isolated_app["session_factory"]()
    try:
        record = BidFile(
            filename="preview.pdf",
            filepath=str(source_path),
            status="completed",
        )
        session.add(record)
        session.commit()
        record_id = record.id
    finally:
        session.close()

    response = client.get(f"/api/files/{record_id}/preview")

    assert response.status_code == 400
    assert response.json()["detail"] == "该文件不使用文本预览"


def test_legacy_doc_piece_table_extracts_unicode_text():
    from app.services.parser import _extract_doc_piece_table

    expected = "旧版招标文件\r资格审查要求"
    file_offset = 512
    word_stream = bytearray(file_offset + len(expected.encode("utf-16le")))
    struct.pack_into("<H", word_stream, 32, 0)  # csw
    struct.pack_into("<H", word_stream, 34, 0)  # cslw
    struct.pack_into("<H", word_stream, 36, 34)  # FibRgFcLcb pairs
    word_stream[file_offset:] = expected.encode("utf-16le")

    plc = bytearray(16)
    struct.pack_into("<II", plc, 0, 0, len(expected))
    struct.pack_into("<I", plc, 10, file_offset)
    table_stream = b"\x02" + struct.pack("<I", len(plc)) + plc
    struct.pack_into("<II", word_stream, 38 + 33 * 8, 0, len(table_stream))

    assert _extract_doc_piece_table(bytes(word_stream), table_stream) == expected


def test_invalid_legacy_doc_preview_returns_clear_error(client, isolated_app, monkeypatch):
    from app.models import BidFile
    from app.services.word_preview import WordConversionError

    source_path = isolated_app["runtime_dir"] / "uploads" / "broken.doc"
    source_path.write_bytes(b"not-an-ole-document")
    session = isolated_app["session_factory"]()
    try:
        record = BidFile(filename="broken.doc", filepath=str(source_path), status="completed")
        session.add(record)
        session.commit()
        record_id = record.id
    finally:
        session.close()

    def fail_conversion(path):
        raise WordConversionError("DOC 文件已损坏或格式无法识别")

    monkeypatch.setattr("app.api.files.ensure_word_preview_pdf", fail_conversion)

    response = client.get(f"/api/files/{record_id}/preview")
    assert response.status_code == 422
    assert "损坏" in response.json()["detail"] or "无效" in response.json()["detail"]
