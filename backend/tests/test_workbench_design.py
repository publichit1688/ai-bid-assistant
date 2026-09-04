import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "docs" / "contracts" / "V1_5_WORKBENCH_CONTRACT.json"
DESIGN_PATH = PROJECT_ROOT / "docs" / "V1_5_WORKBENCH_DESIGN.md"


def test_workbench_contract_requires_human_confirmation_and_sources():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["review_statuses"] == ["suggested", "confirmed", "rejected"]
    assert contract["invariants"]["ai_results_start_as_suggestions"] is True
    assert contract["invariants"]["confirmed_content_is_never_silently_overwritten"] is True
    assert contract["invariants"]["criterion_source_is_required"] is True
    assert "source_ref_id" in contract["entities"]["criterion"]


def test_workbench_contract_excludes_full_bid_generation_and_submission():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["invariants"]["one_click_full_bid_generation"] is False
    assert contract["invariants"]["automatic_bid_submission"] is False


def test_workbench_design_covers_v1_protection_and_conflicts():
    design = DESIGN_PATH.read_text(encoding="utf-8")

    assert "不改变上传、风险分析、PDF/Word预览、Dashboard、项目对比和报告接口" in design
    assert "HTTP 409" in design
    assert "不自动调用AI" in design
    assert "不在Dashboard增加卡片" in design
