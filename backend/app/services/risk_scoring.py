"""Canonical risk counting and scoring rules shared by every API surface."""

FATAL_KEYWORDS = (
    "废标",
    "否决投标",
    "资格审查",
    "保证金",
    "电子签名",
    "签章",
    "人员证书",
    "安全生产许可证",
    "企业资质",
)

BASE_DEDUCTIONS = {
    "high": 20,
    "middle": 8,
    "low": 3,
    "unknown": 5,
}


def classify_risk_level(level):
    """Map free-form Chinese risk labels to one and only one bucket."""
    value = str(level or "").strip()
    if "高" in value:
        return "high"
    if "中" in value:
        return "middle"
    if "低" in value:
        return "low"
    return "unknown"


def calculate_risk_deduction(risk):
    """Return a safe 0..25 deduction, including legacy fallback scoring."""
    if not isinstance(risk, dict):
        return 0

    saved_deduction = risk.get("deduction")
    if saved_deduction is not None:
        try:
            deduction = int(saved_deduction)
        except (TypeError, ValueError, OverflowError):
            deduction = 0
        return max(0, min(deduction, 25))

    bucket = classify_risk_level(risk.get("level"))
    deduction = BASE_DEDUCTIONS[bucket]
    risk_text = f"{risk.get('keyword') or ''} {risk.get('reason') or ''}"
    if any(word in risk_text for word in FATAL_KEYWORDS):
        deduction += 5
    return min(deduction, 25)


def calculate_risk_summary(risk_data):
    """Build the stable score contract used by list, detail and Dashboard APIs."""
    risks = [risk for risk in risk_data if isinstance(risk, dict)] if isinstance(risk_data, list) else []
    counts = {"high": 0, "middle": 0, "low": 0}

    total_deduction = 0
    for risk in risks:
        bucket = classify_risk_level(risk.get("level"))
        if bucket in counts:
            counts[bucket] += 1
        total_deduction += calculate_risk_deduction(risk)

    score = max(100 - total_deduction, 0)
    if score >= 85:
        score_level = "低风险"
    elif score >= 70:
        score_level = "中低风险"
    elif score >= 60:
        score_level = "中风险"
    elif score >= 40:
        score_level = "高风险"
    else:
        score_level = "极高风险"

    return {
        "score": score,
        "score_level": score_level,
        "risk_count": len(risks),
        "high_count": counts["high"],
        "middle_count": counts["middle"],
        "low_count": counts["low"],
        "total_deduction": total_deduction,
    }
