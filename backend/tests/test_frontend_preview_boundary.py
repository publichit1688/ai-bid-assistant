from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
APP_SOURCE = (FRONTEND_ROOT / "src" / "App.jsx").read_text(encoding="utf-8")
PREVIEW_SOURCE = (
    FRONTEND_ROOT / "src" / "components" / "DocumentPreview.jsx"
).read_text(encoding="utf-8")
PREVIEW_CSS = (FRONTEND_ROOT / "src" / "pdf-highlight.css").read_text(
    encoding="utf-8"
)
LAYOUT_CSS = (FRONTEND_ROOT / "src" / "index.css").read_text(encoding="utf-8")


def test_pdf_runtime_and_protected_blob_lifecycle_are_explicit():
    assert 'from "react-pdf"' not in APP_SOURCE
    assert 'lazy(()=>import("./components/DocumentPreview.jsx"))' in APP_SOURCE
    assert 'from "react-pdf"' in PREVIEW_SOURCE
    assert 'window.location.origin + "/pdf.worker.min.mjs"' in PREVIEW_SOURCE
    assert 'responseType:"blob"' in APP_SOURCE
    assert "window.URL.createObjectURL(response.data)" in APP_SOURCE
    assert "window.URL.revokeObjectURL(pdfObjectUrlRef.current)" in APP_SOURCE
    assert "useEffect(()=>()=>clearPdfObjectUrl(),[])" in APP_SOURCE


def test_pdf_width_remains_container_driven_and_capped():
    assert "new ResizeObserver(updatePdfWidth)" in PREVIEW_SOURCE
    assert "Math.floor(container.getBoundingClientRect().width)" in PREVIEW_SOURCE
    assert "Math.min(700, availableWidth)" in PREVIEW_SOURCE
    assert "const pdfContainerRef = useRef(null)" in PREVIEW_SOURCE
    assert "const [pdfPageWidth, setPdfPageWidth] = useState(700)" in PREVIEW_SOURCE
    assert "pdfContainerRef={pdfContainerRef}" not in APP_SOURCE
    assert "pdfPageWidth={pdfPageWidth}" not in APP_SOURCE
    assert 'className="pdf-responsive-container"' in PREVIEW_SOURCE
    assert ".pdf-responsive-container" in LAYOUT_CSS
    assert "overflow: hidden" in LAYOUT_CSS


def test_pdf_page_keeps_text_annotation_and_navigation_contracts():
    assert "<Document" in PREVIEW_SOURCE
    assert "onLoadSuccess={onDocumentLoad}" in PREVIEW_SOURCE
    assert "<Page" in PREVIEW_SOURCE
    assert "pageNumber={pageNumber}" in PREVIEW_SOURCE
    assert "renderTextLayer={true}" in PREVIEW_SOURCE
    assert "renderAnnotationLayer={true}" in PREVIEW_SOURCE
    assert "width={pdfPageWidth}" in PREVIEW_SOURCE
    assert "pageNumber <= 1" in PREVIEW_SOURCE
    assert "pageNumber >= numPages" in PREVIEW_SOURCE
    assert "onPreviousPage" in PREVIEW_SOURCE
    assert "onNextPage" in PREVIEW_SOURCE
    assert "onDocumentLoad={(pdf)=>setNumPages(pdf.numPages)}" in APP_SOURCE
    assert "onPreviousPage={()=>setPageNumber(pageNumber - 1)}" in APP_SOURCE
    assert "onNextPage={()=>setPageNumber(pageNumber + 1)}" in APP_SOURCE


def test_word_rendered_preview_and_legacy_fallback_remain_distinct():
    assert 'response.data?.pagination === "rendered"' in APP_SOURCE
    assert "setWordPreviewRiskPages(response.data?.risk_page_map || {})" in APP_SOURCE
    assert "await loadProtectedPdf(response.data.filepath)" in APP_SOURCE
    assert "setDocxPreviewPages(pages)" in APP_SOURCE
    assert "renderHighlightedDocxText(" in PREVIEW_SOURCE
    assert 'className="docx-preview-page"' in PREVIEW_SOURCE


def test_risk_navigation_preserves_word_page_mapping_and_text_highlight():
    assert 'Number(wordPreviewRiskPages[String(index)])' in APP_SOURCE
    assert "Math.min(Math.max(requestedPage, 1), numPages)" in APP_SOURCE
    assert "setActiveRiskPreviewPage(targetPage)" in APP_SOURCE
    assert "setPageNumber(" in APP_SOURCE
    assert "highlightKeyword(" in APP_SOURCE
    assert 'document.querySelectorAll(\n".react-pdf__Page__textContent span"' in APP_SOURCE


def test_ocr_boxes_remain_normalized_and_bound_to_the_active_page():
    assert "Number(activeRisk?.page) === pageNumber" in PREVIEW_SOURCE
    assert "Array.isArray(activeRisk?.ocr_highlight_boxes)" in PREVIEW_SOURCE
    for coordinate in ("x", "y", "width", "height"):
        assert f"Number(box.{coordinate}) * 100" in PREVIEW_SOURCE
    for class_name in (
        ".ocr-highlight-layer",
        ".ocr-highlight-box",
        ".ocr-highlight-high",
        ".ocr-highlight-middle",
        ".ocr-highlight-low",
    ):
        assert class_name in PREVIEW_CSS
