import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.database import SessionLocal
from app.models import BidFile
from app.services.risk_location import map_risks_to_rendered_pages
from app.services.risk_scoring import calculate_risk_summary
from app.services.word_preview import (
    WordConversionError,
    WordRendererNotConfiguredError,
    ensure_word_preview_pdf,
    extract_preview_pdf_pages,
    get_preview_renderer,
    get_word_preview_path,
    inspect_preview_pdf,
)
from app.services.storage_paths import (
    UnsafeStoragePathError,
    public_upload_path,
    resolve_upload_file,
)


router = APIRouter()


@router.get("/files/{file_id}/preview")
def get_file_preview(file_id: int):
    """Render Word files to a PDF derivative with layout-backed pagination."""
    db = SessionLocal()
    try:
        record = db.query(BidFile).filter(BidFile.id == file_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="文件不存在")

        try:
            source_path = resolve_upload_file(record.filepath, require_file=True)
        except UnsafeStoragePathError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "UNSAFE_STORED_PATH",
                    "message": "历史文件路径不安全，已阻止访问。",
                },
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="源文件不存在") from exc
        suffix = source_path.suffix.lower()
        if suffix not in {".docx", ".doc"}:
            raise HTTPException(status_code=400, detail="该文件不使用文本预览")
        try:
            preview_path = ensure_word_preview_pdf(source_path)
            preview_path = resolve_upload_file(preview_path, require_file=True)
            page_count = inspect_preview_pdf(preview_path)
            preview_pages = extract_preview_pdf_pages(preview_path)
        except WordRendererNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except WordConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            risks = json.loads(record.risk or "[]")
        except (TypeError, json.JSONDecodeError):
            risks = []
        return {
            "format": "pdf",
            "source_format": suffix.lstrip("."),
            "pagination": "rendered",
            "filepath": public_upload_path(preview_path),
            "num_pages": page_count,
            "renderer": get_preview_renderer(preview_path),
            "risk_page_map": map_risks_to_rendered_pages(risks, preview_pages),
        }
    finally:
        db.close()


# ==================================
# 获取历史文件列表
# GET /api/files
# ==================================

@router.get("/files")
def get_files():

    db = SessionLocal()

    try:

        files = db.query(
            BidFile
        ).all()


        result = []


        for item in files:

            risk_data = []


            if item.risk:

                try:

                    risk_data = json.loads(
                        item.risk
                    )

                except Exception:

                    risk_data = []


            summary = calculate_risk_summary(
                risk_data
            )


            result.append({

                "id":
                item.id,

                "filename":
                item.filename,

                "filepath":
                public_upload_path(item.filepath),

                "project_name":
                item.project_name,

                "score":
                summary["score"],

                "score_level":
                summary["score_level"],

                "risk_count":
                summary["risk_count"],

                "high_count":
                summary["high_count"],

                "middle_count":
                summary["middle_count"],

                "low_count":
                summary["low_count"],

                "total_deduction":
                summary["total_deduction"],

                "status":
                item.status,

                "created_time":
                str(item.created_time)

            })


        return result


    finally:

        db.close()


# ==================================
# 获取历史文件详情
# GET /api/files/{file_id}
# ==================================

@router.get("/files/{file_id}")
def get_file_detail(file_id: int):

    db = SessionLocal()

    try:

        file = db.query(
            BidFile
        ).filter(
            BidFile.id == file_id
        ).first()


        if not file:

            return {
                "error": "文件不存在"
            }


        analysis = {}

        if file.analysis:

            try:

                analysis = json.loads(
                    file.analysis
                )

            except Exception:

                analysis = {}


        risk = []

        if file.risk:

            try:

                risk = json.loads(
                    file.risk
                )

            except Exception:

                risk = []


        summary = calculate_risk_summary(
            risk
        )


        return {

            "id":
            file.id,

            "filename":
            file.filename,

            "filepath":
            public_upload_path(file.filepath),

            "project_name":
            file.project_name,

            "score":
            summary["score"],

            "score_level":
            summary["score_level"],

            "risk_count":
            summary["risk_count"],

            "high_count":
            summary["high_count"],

            "middle_count":
            summary["middle_count"],

            "low_count":
            summary["low_count"],

            "total_deduction":
            summary["total_deduction"],

            "status":
            file.status,

            "created_time":
            str(file.created_time),

            "analysis":
            analysis,

            "risk":
            risk

        }


    finally:

        db.close()


# ==================================
# 删除历史记录
# DELETE /api/files/{file_id}
#
# delete_original=false
# 只删除数据库记录
#
# delete_original=true
# 删除数据库记录 + 原文件
# ==================================

@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    delete_original: bool = False
):

    db = SessionLocal()

    try:

        file = db.query(
            BidFile
        ).filter(
            BidFile.id == file_id
        ).first()


        if not file:

            return {
                "success": False,
                "error": "文件不存在"
            }


        filepath = file.filepath


        # 删除数据库记录
        db.delete(file)

        db.commit()


        original_deleted = False
        cleanup_status = "not_requested"


        # 是否删除服务器原文件
        if delete_original and filepath:
            cleanup_status = "not_found"
            try:
                safe_path = resolve_upload_file(filepath)
                if safe_path.is_file():
                    safe_path.unlink()
                    original_deleted = True
                    cleanup_status = "deleted"
                preview_path = resolve_upload_file(get_word_preview_path(safe_path))
                if preview_path.is_file():
                    preview_path.unlink()
            except UnsafeStoragePathError:
                cleanup_status = "unsafe_path"
                print("原文件路径越界，已阻止物理删除")
            except OSError as exc:
                cleanup_status = "failed"
                print("删除原文件失败:", type(exc).__name__)


        return {

            "success":
            True,

            "message":
            (
                "历史记录和原文件已删除"
                if original_deleted
                else "历史记录已删除"
            ),

            "id":
            file_id,

            "original_deleted":
            original_deleted,

            "file_cleanup_status":
            cleanup_status

        }


    except Exception as exc:

        db.rollback()

        print("删除失败:", type(exc).__name__)

        return {

            "success":
            False,

            "error":
            "删除失败，请稍后重试。"

        }


    finally:

        db.close()
