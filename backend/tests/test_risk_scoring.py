import pytest

from app.services.risk_scoring import (
    calculate_risk_deduction,
    calculate_risk_summary,
    classify_risk_level,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("高风险", "high"),
        ("中风险", "middle"),
        ("中低风险", "middle"),
        ("低风险", "low"),
        (None, "unknown"),
        ("", "unknown"),
    ],
)
def test_risk_level_has_exactly_one_bucket(label, expected):
    assert classify_risk_level(label) == expected


@pytest.mark.parametrize(
    ("risk", "expected"),
    [
        ({"level": "高风险", "reason": "可能废标"}, 25),
        ({"level": "中风险"}, 8),
        ({"level": "低风险"}, 3),
        ({"level": None}, 5),
        ({"level": "高风险", "deduction": "12"}, 12),
        ({"level": "高风险", "deduction": 99}, 25),
        ({"level": "高风险", "deduction": -4}, 0),
        ({"level": "高风险", "deduction": "损坏"}, 0),
        (None, 0),
    ],
)
def test_deduction_is_compatible_and_bounded(risk, expected):
    assert calculate_risk_deduction(risk) == expected


def test_summary_handles_empty_and_malformed_values():
    empty_summary = {
        "score": 100,
        "score_level": "低风险",
        "risk_count": 0,
        "high_count": 0,
        "middle_count": 0,
        "low_count": 0,
        "total_deduction": 0,
    }
    assert calculate_risk_summary(None) == empty_summary
    assert calculate_risk_summary({"level": "高风险"}) == empty_summary

    summary = calculate_risk_summary(
        [
            {"level": "高风险", "reason": "可能废标"},
            {"level": "中风险", "deduction": "8"},
            {"level": "低风险", "deduction": -4},
            {"level": "中低风险"},
            {"level": None},
            {"level": "高风险", "deduction": "损坏"},
            "损坏条目",
        ]
    )

    assert summary == {
        "score": 54,
        "score_level": "高风险",
        "risk_count": 6,
        "high_count": 2,
        "middle_count": 2,
        "low_count": 1,
        "total_deduction": 46,
    }
