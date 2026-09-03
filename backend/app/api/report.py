from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.report import create_report


router = APIRouter()



@router.post("/report")
def generate_report(data:dict):


    path=create_report(data)


    return FileResponse(

        path,

        filename="AI投标风险分析报告.docx",

        media_type=
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    )