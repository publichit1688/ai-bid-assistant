from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.compare_report import create_compare_report


router = APIRouter()


@router.post("/compare-report")
def generate_compare_report(data: dict):

    path = create_compare_report(
        data
    )

    return FileResponse(

        path,

        filename="AI投标项目对比分析报告.docx",

        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    )