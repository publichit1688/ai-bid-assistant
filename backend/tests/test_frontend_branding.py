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


def test_project_center_avoids_deprecated_antd_list():
    app_source = (FRONTEND_ROOT / "src" / "App.jsx").read_text(encoding="utf-8")

    assert "  List," not in app_source
    assert "<List" not in app_source
    assert 'role="list" aria-label="项目列表"' in app_source
    assert 'role="listitem"' in app_source
    assert '<EmptyState description="暂无项目记录" />' in app_source


def test_workbench_page_is_lazy_loaded_from_its_own_module():
    app_source = (FRONTEND_ROOT / "src" / "App.jsx").read_text(encoding="utf-8")
    workbench_source = (
        FRONTEND_ROOT / "src" / "pages" / "WorkbenchPage.jsx"
    ).read_text(encoding="utf-8")

    assert 'lazy(()=>import("./pages/WorkbenchPage.jsx"))' in app_source
    assert '<Suspense fallback={<LoadingState text="正在加载智能编标工作台..." />}' in app_source
    assert "function WorkbenchPage(" not in app_source
    assert "export default function WorkbenchPage(" in workbench_source
    for callback in (
        "onReload",
        "onRunAi",
        "onReview",
        "onEditMaterial",
        "onAddMaterial",
        "onAddSection",
        "onMapCriterion",
    ):
        assert callback in app_source
        assert callback in workbench_source


def test_dashboard_charts_are_lazy_loaded_without_moving_dashboard_state():
    app_source = (FRONTEND_ROOT / "src" / "App.jsx").read_text(encoding="utf-8")
    chart_source = (
        FRONTEND_ROOT / "src" / "components" / "DashboardChart.jsx"
    ).read_text(encoding="utf-8")

    assert 'import ReactECharts from "echarts-for-react"' not in app_source
    assert 'lazy(()=>import("./components/DashboardChart.jsx"))' in app_source
    assert 'from "echarts-for-react/esm/core"' in chart_source
    assert 'from "echarts/core"' in chart_source
    assert 'from "echarts/charts"' in chart_source
    assert 'from "echarts/components"' in chart_source
    assert 'from "echarts/renderers"' in chart_source
    assert 'from "echarts-for-react"' not in chart_source
    for module_name in (
        "BarChart",
        "LineChart",
        "PieChart",
        "GridComponent",
        "LegendComponent",
        "TooltipComponent",
        "CanvasRenderer",
    ):
        assert module_name in chart_source
    assert app_source.count("<AsyncDashboardChart") == 4
    for option_name in (
        "riskChartOption",
        "scoreChartOption",
        "analysisTrendOption",
        "riskTrendOption",
    ):
        assert f"option={{{option_name}}}" in app_source
