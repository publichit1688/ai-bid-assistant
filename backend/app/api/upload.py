import os
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import get_upload_dir, get_upload_max_bytes
from app.services.parser import DocumentParseError, parse_document
from app.services.ocr import OCRConfigurationError, OCRServiceError
from app.services.llm import analyze_bid

from app.database import SessionLocal
from app.models import BidFile
from app.services.risk_scoring import calculate_risk_summary
from app.services.ai_errors import AIResponseFormatError, to_ai_http_exception
from app.services.risk_location import (
    attach_ocr_highlight_boxes,
    ensure_locatable_highlights,
)
from app.services.word_preview import (
    WordConversionError,
    WordRendererNotConfiguredError,
    get_word_preview_path,
)
from app.services.upload_validation import (
    UploadValidationError,
    validate_declared_mime,
    validate_file_signature,
)
from app.services.storage_paths import public_upload_path


router = APIRouter()

UPLOAD_DIR = get_upload_dir()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_request_upload(*paths):
    """Remove only exact files created by the current upload request."""
    upload_root = Path(UPLOAD_DIR).resolve()
    for path in paths:
        if path is None:
            continue
        resolved = Path(path).resolve()
        if resolved.parent != upload_root:
            continue
        try:
            resolved.unlink(missing_ok=True)
        except OSError as exc:
            print("上传临时文件清理失败:", type(exc).__name__)


def copy_upload_with_limit(source, destination, max_bytes, chunk_size=1024 * 1024):
    total_bytes = 0
    while True:
        chunk = source.read(chunk_size)
        if not chunk:
            return total_bytes
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "UPLOAD_TOO_LARGE",
                    "message": f"文件超过上传大小上限（{max_bytes // (1024 * 1024)} MB）。",
                },
            )
        destination.write(chunk)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...)
):

    db = SessionLocal()
    temporary_path = None
    final_path = None
    temporary_preview_path = None
    final_preview_path = None
    database_committed = False

    try:

        # =========================
        # 1. 保存上传文件
        # =========================

        original_filename = Path(
            (file.filename or "upload.bin").replace("\\", "/")
        ).name or "upload.bin"
        suffix = Path(original_filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".doc"}:
            raise HTTPException(
                status_code=415,
                detail={
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": "仅支持 PDF、DOCX 和 DOC 文件。",
                },
            )
        validate_declared_mime(suffix, file.content_type)
        upload_token = uuid4().hex
        temporary_path = Path(UPLOAD_DIR) / f".{upload_token}.uploading{suffix}"
        final_path = Path(UPLOAD_DIR) / f"{upload_token}_{original_filename}"
        filepath = str(temporary_path)

        with open(
            temporary_path,
            "wb"
        ) as buffer:

            copy_upload_with_limit(
                file.file,
                buffer,
                get_upload_max_bytes(),
            )

        validate_file_signature(temporary_path, suffix)

        # =========================
        # 2. PDF / DOCX 分页解析
        # =========================

        if suffix in {".doc", ".docx"}:
            temporary_preview_path = get_word_preview_path(temporary_path)

        pages = parse_document(
            filepath
        )

        print(
            "解析页数:",
            len(pages)
        )


        # =========================
        # 3. 拼接 AI 输入
        # =========================

        full_text = ""

        for item in pages:

            full_text += (
                "\n\n"
                f"【第{item['page']}页】\n"
                +
                item["text"]
            )

        # =========================
        # 4. AI分析
        # =========================

        try:
            result = analyze_bid(full_text)
        except Exception as exc:
            raise to_ai_http_exception(exc) from exc

        # 防止 AI 返回 error 后继续写数据库
        if not isinstance(result, dict):

            raise AIResponseFormatError(
                "AI返回格式错误"
            )

        if result.get("error"):

            raise AIResponseFormatError(
                result.get("error")
            )

        print(
            "AI分析完成"
        )


        # =========================
        # 5. 获取风险数据
        # =========================

        risk_data = result.get(
            "risk",
            []
        )

        if not isinstance(risk_data, list):

            risk_data = []

        # 忽略 AI 返回的损坏条目，确保后续所有接口采用同一有效风险集合。
        risk_data = [
            risk
            for risk in risk_data
            if isinstance(risk, dict)
        ]
        ensure_locatable_highlights(risk_data, pages)
        attach_ocr_highlight_boxes(risk_data, pages)

        print(
            "风险数量:",
            len(risk_data)
        )


        # =========================
        # 6. 项目基本数据
        # =========================

        project_name = (
            result.get("project_name")
            or "未找到"
        )

        risk_count = len(
            risk_data
        )


        # =========================
        # 8. AI投标风险评分 V2
        # =========================

        score = 100


        # 容易造成废标 / 否决投标的关键词
        fatal_keywords = [

            "废标",
            "否决投标",
            "资格审查",
            "保证金",
            "电子签名",
            "签章",
            "人员证书",
            "安全生产许可证",
            "企业资质"

        ]


        for risk in risk_data:

            level = str(
                risk.get("level", "")
            )

            keyword = str(
                risk.get("keyword", "")
            )

            reason = str(
                risk.get("reason", "")
            )

            risk_text = (
                keyword
                + " "
                + reason
            )


            # =========================
            # 1. 基础风险扣分
            # =========================

            deduction_reasons = []


            if "高" in level:

                deduction = 20

                deduction_reasons.append(
                    "高风险基础扣20分"
                )


            elif "中" in level:

                deduction = 8

                deduction_reasons.append(
                    "中风险基础扣8分"
                )


            elif "低" in level:

                deduction = 3

                deduction_reasons.append(
                    "低风险基础扣3分"
                )


            else:

                deduction = 5

                deduction_reasons.append(
                    "风险等级不明确，基础扣5分"
                )


            # =========================
            # 2. 致命风险额外扣分
            # =========================

            matched_fatal = []

            for word in fatal_keywords:

                if word in risk_text:

                    matched_fatal.append(
                        word
                    )


            if matched_fatal:

                deduction += 5

                deduction_reasons.append(
                    "涉及关键废标风险（"
                    +
                    "、".join(matched_fatal)
                    +
                    "），额外扣5分"
                )


            # =========================
            # 3. 单项最高扣25分
            # =========================

            deduction = min(
                deduction,
                25
            )


            # =========================
            # 4. 写回风险对象
            # =========================

            risk["deduction"] = deduction

            risk["deduction_reason"] = (
                "；".join(
                    deduction_reasons
                )
            )


            # =========================
            # 5. 总评分扣分
            # =========================

            score -= deduction
        # 上传响应、历史文件和 Dashboard 共用同一评分契约。
        summary = calculate_risk_summary(risk_data)
        score = summary["score"]
        score_level = summary["score_level"]
        risk_count = summary["risk_count"]
        high_count = summary["high_count"]
        middle_count = summary["middle_count"]
        low_count = summary["low_count"]
        total_deduction = summary["total_deduction"]

        # 分析全部成功后再将临时文件原子移动为正式文件。
        os.replace(temporary_path, final_path)
        if suffix in {".doc", ".docx"}:
            final_preview_path = get_word_preview_path(final_path)
            os.replace(temporary_preview_path, final_preview_path)
        filepath = str(final_path)


        # =========================
        # 11. 保存数据库
        # =========================

        record = BidFile(

            filename=original_filename,

            filepath=filepath,

            project_name=project_name,

            score=score,

            risk_count=risk_count,

            analysis=json.dumps(
                result,
                ensure_ascii=False
            ),

            risk=json.dumps(
                risk_data,
                ensure_ascii=False
            ),

            status="completed"

        )


        db.add(
            record
        )

        db.commit()
        database_committed = True

        db.refresh(
            record
        )


        # =========================
        # 12. 返回前端
        # =========================

        return {

            "id": record.id,

            "filename": record.filename,

            "filepath": public_upload_path(record.filepath),

            "status": record.status,

            "project_name": record.project_name,

            "score": record.score,

           "score_level": score_level,

           "risk_count": record.risk_count,

           "high_count": high_count,

           "middle_count": middle_count,

           "low_count": low_count,

            "total_deduction": total_deduction,

            "analysis": result,

           "risk": risk_data
       }


    except OCRConfigurationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "OCR_NOT_CONFIGURED", "message": str(exc)},
        ) from exc

    except OCRServiceError as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail={"code": "OCR_SERVICE_ERROR", "message": str(exc)},
        ) from exc

    except WordRendererNotConfiguredError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "WORD_RENDERER_NOT_CONFIGURED", "message": str(exc)},
        ) from exc

    except WordConversionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "WORD_CONVERSION_ERROR", "message": str(exc)},
        ) from exc

    except DocumentParseError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOCUMENT_PARSE_ERROR", "message": str(exc)},
        ) from exc

    except UploadValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except AIResponseFormatError as exc:
        db.rollback()
        raise to_ai_http_exception(exc) from exc

    except Exception as exc:

        db.rollback()
        print("上传处理失败:", type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "UPLOAD_PROCESSING_ERROR",
                "message": "文件处理失败，请检查文件后重试。",
            },
        ) from exc


    finally:
        if not database_committed:
            cleanup_request_upload(
                temporary_path,
                final_path,
                temporary_preview_path,
                final_preview_path,
            )
        db.close()
