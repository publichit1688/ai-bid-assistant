from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def test_frontend_uses_product_metadata_and_favicon():
    html = (FRONTEND_ROOT / "index.html").read_text(encoding="utf-8")
    favicon = (FRONTEND_ROOT / "public" / "favicon.svg").read_text(
        encoding="utf-8"
    )

    assert '<html lang="zh-CN">' in html
    assert "<title>AI标书助手</title>" in html
    assert 'name="description"' in html
    assert 'href="/favicon.svg"' in html
    assert "AI标书助手" in favicon


def test_unused_vite_template_assets_are_absent_but_pdf_worker_remains():
    removed = (
        FRONTEND_ROOT / "public" / "icons.svg",
        FRONTEND_ROOT / "src" / "assets" / "hero.png",
        FRONTEND_ROOT / "src" / "assets" / "react.svg",
        FRONTEND_ROOT / "src" / "assets" / "vite.svg",
    )

    assert all(not path.exists() for path in removed)
    assert (FRONTEND_ROOT / "public" / "pdf.worker.min.mjs").is_file()
