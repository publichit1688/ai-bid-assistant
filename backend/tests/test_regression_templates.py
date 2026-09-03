import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGRESSION_DOCS = PROJECT_ROOT / "docs" / "regression"


def test_expected_result_template_is_valid_json():
    template = json.loads(
        (REGRESSION_DOCS / "EXPECTED_RESULT.template.json").read_text(
            encoding="utf-8"
        )
    )

    assert template["template_version"] == "1.0"
    assert template["authorization"]["status"] == "待确认"
    assert set(template["expected_summary"]) == {
        "score",
        "score_level",
        "risk_count",
        "high_count",
        "middle_count",
        "low_count",
        "total_deduction",
    }


def test_sample_registry_has_safe_unique_coverage_slots():
    with (REGRESSION_DOCS / "SAMPLE_REGISTRY.csv").open(
        encoding="utf-8-sig", newline=""
    ) as source:
        rows = list(csv.DictReader(source))

    required_columns = {
        "sample_id",
        "authorization_status",
        "execution_status",
        "source_format",
        "text_mode",
        "expected_coverage",
        "contains_personal_data",
    }
    assert rows
    assert required_columns.issubset(rows[0])
    assert len({row["sample_id"] for row in rows}) == len(rows)
    assert all(row["sample_id"].startswith("RB-") for row in rows)
    allowed_authorization = {"待确认", "已确认", "已撤销", "禁止使用"}
    allowed_execution = {
        "未执行",
        "格式回归通过",
        "格式与定位回归通过",
        "部分通过",
        "失败",
        "阻塞",
    }
    assert all(row["authorization_status"] in allowed_authorization for row in rows)
    assert all(row["execution_status"] in allowed_execution for row in rows)
    confirmed = {
        row["sample_id"]
        for row in rows
        if row["authorization_status"] == "已确认"
    }
    assert confirmed == {
        "RB-PDF-TEXT-SHORT",
        "RB-PDF-TEXT-LONG",
        "RB-PDF-SCAN",
        "RB-PDF-SCAN-PURE",
        "RB-PDF-TABLE",
        "RB-DOCX-TEXT",
        "RB-INVALID-FILE",
    }
    assert not any("\\" in value or ":/" in value for row in rows for value in row.values())


def test_v1_regression_report_covers_every_registered_sample():
    with (REGRESSION_DOCS / "SAMPLE_REGISTRY.csv").open(
        encoding="utf-8-sig", newline=""
    ) as source:
        sample_ids = {row["sample_id"] for row in csv.DictReader(source)}

    report = (
        REGRESSION_DOCS / "V1_REAL_DOCUMENT_REGRESSION_REPORT.md"
    ).read_text(encoding="utf-8")

    assert all(sample_id in report for sample_id in sample_ids)
    assert "P3完成前不得宣布V1发布" in report
    assert "已知限制" in report
