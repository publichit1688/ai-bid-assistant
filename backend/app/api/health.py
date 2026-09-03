from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.runtime_checks import readiness_report

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "AI Bid Assistant"
    }


@router.get("/health/ready")
def readiness():
    report = readiness_report()
    return JSONResponse(
        status_code=200 if report["status"] == "ready" else 503,
        content=report,
    )
