from fastapi import APIRouter

from app.services.llm import analyze_compare_decision
from app.services.ai_errors import to_ai_http_exception


router = APIRouter()


@router.post("/compare/ai-decision")
def ai_compare_decision(data: dict):

    try:

        result = analyze_compare_decision(
            data
        )

        return {
            "success": True,
            "ai_decision": result
        }

    except Exception as exc:
        print("项目AI决策分析失败:", type(exc).__name__)
        raise to_ai_http_exception(exc) from exc
