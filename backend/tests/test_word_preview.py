from pathlib import Path

import fitz


def write_pdf(path, page_count):
    document = fitz.open()
    for page_number in range(page_count):
        page = document.new_page()
        page.insert_text((72, 72), f"page {page_number + 1}")
    document.save(path)
    document.close()


def test_word_preview_conversion_creates_valid_pdf(tmp_path, monkeypatch):
    from app.services import word_preview

    source = tmp_path / "招标文件.docx"
    source.write_bytes(b"docx-placeholder")
    target = word_preview.get_word_preview_path(source)
    monkeypatch.setattr(
        word_preview,
        "configured_renderers",
        lambda: ("microsoft_word", "wps"),
    )
    monkeypatch.setattr(
        word_preview,
        "find_renderer_executable",
        lambda renderer: Path(f"C:/{renderer}.exe"),
    )
    used_renderers = []

    def fake_run(renderer, _source, rendered_path, _timeout):
        used_renderers.append(renderer)
        write_pdf(rendered_path, page_count=3)

    monkeypatch.setattr(word_preview, "_run_office_automation", fake_run)

    result = word_preview.ensure_word_preview_pdf(source)

    assert result == target.resolve()
    assert result.is_file()
    assert word_preview.inspect_preview_pdf(result) == 3
    assert used_renderers == ["microsoft_word"]


def test_word_preview_falls_back_to_wps_when_word_fails(tmp_path, monkeypatch):
    from app.services import word_preview

    source = tmp_path / "fallback.docx"
    source.write_bytes(b"docx-placeholder")
    monkeypatch.setattr(
        word_preview,
        "configured_renderers",
        lambda: ("microsoft_word", "wps"),
    )
    monkeypatch.setattr(
        word_preview,
        "find_renderer_executable",
        lambda renderer: Path(f"C:/{renderer}.exe"),
    )
    used_renderers = []

    def fake_run(renderer, _source, rendered_path, _timeout):
        used_renderers.append(renderer)
        if renderer == "microsoft_word":
            raise word_preview.WordConversionError("Word is unavailable")
        write_pdf(rendered_path, page_count=2)

    monkeypatch.setattr(word_preview, "_run_office_automation", fake_run)

    result = word_preview.ensure_word_preview_pdf(source)

    assert word_preview.inspect_preview_pdf(result) == 2
    assert used_renderers == ["microsoft_word", "wps"]


def test_word_preview_reuses_fresh_cached_pdf(tmp_path, monkeypatch):
    from app.services import word_preview

    source = tmp_path / "cached.doc"
    source.write_bytes(b"doc-placeholder")
    target = word_preview.get_word_preview_path(source)
    write_pdf(target, page_count=2)

    def renderer_should_not_be_used(_renderer):
        raise AssertionError("fresh preview should be reused")

    monkeypatch.setattr(
        word_preview,
        "find_renderer_executable",
        renderer_should_not_be_used,
    )

    assert word_preview.ensure_word_preview_pdf(source) == target.resolve()
    assert word_preview.inspect_preview_pdf(target) == 2
