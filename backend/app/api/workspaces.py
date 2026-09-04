import json
import hashlib
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import update

from app.database import SessionLocal
from app.models import (
    BidFile,
    BidWorkspace,
    CriterionSectionMapping,
    OutlineSection,
    ResponseMaterial,
    ScoringCriterion,
    SourceReference,
    WorkspaceRevision,
)
from app.services.ai_errors import AIResponseFormatError, to_ai_http_exception
from app.services.llm import generate_outline_suggestions, generate_scoring_criteria
from app.services.parser import DocumentParseError, parse_document
from app.services.storage_paths import UnsafeStoragePathError, resolve_upload_file


router = APIRouter()


class WorkspaceCreate(BaseModel):
    bid_file_id: int = Field(gt=0)
    title: str | None = Field(default=None, max_length=200)


class SectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    revision: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)


class SectionUpdate(BaseModel):
    revision: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    sort_order: int | None = Field(default=None, ge=0)


class OutlineSuggestionCreate(BaseModel):
    revision: int = Field(gt=0)


class SectionReviewUpdate(BaseModel):
    decision: Literal["accept", "reject"]
    revision: int = Field(gt=0)


class CriteriaExtractionCreate(BaseModel):
    revision: int = Field(gt=0)


class MappingItem(BaseModel):
    criterion_id: int = Field(gt=0)
    section_id: int = Field(gt=0)
    rationale: str | None = Field(default=None, max_length=2000)


class MappingUpsert(BaseModel):
    revision: int = Field(gt=0)
    mappings: list[MappingItem] = Field(min_length=1)


MaterialStatus = Literal["pending", "in_progress", "completed", "blocked"]


class MaterialCreate(BaseModel):
    revision: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    criterion_id: int | None = Field(default=None, gt=0)
    section_id: int | None = Field(default=None, gt=0)
    material_status: MaterialStatus = "pending"
    owner_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)


class MaterialUpdate(BaseModel):
    revision: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    material_status: MaterialStatus | None = None
    owner_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)


def _section_payload(section):
    return {
        "id": section.id,
        "parent_id": section.parent_id,
        "stable_key": section.stable_key,
        "title": section.title,
        "sort_order": section.sort_order,
        "origin": section.origin,
        "review_status": section.review_status,
        "source_ref_id": section.source_ref_id,
    }


def _source_payload(source):
    return {
        "id": source.id,
        "page": source.page,
        "quote": source.quote,
        "locator": json.loads(source.locator) if source.locator else None,
        "fingerprint": source.fingerprint,
    }


def _criterion_payload(criterion):
    return {
        "id": criterion.id,
        "stable_key": criterion.stable_key,
        "title": criterion.title,
        "requirement": criterion.requirement,
        "max_score": float(criterion.max_score) if criterion.max_score is not None else None,
        "review_status": criterion.review_status,
        "source_ref_id": criterion.source_ref_id,
    }


def _mapping_payload(mapping):
    return {
        "id": mapping.id,
        "criterion_id": mapping.criterion_id,
        "section_id": mapping.section_id,
        "coverage_status": mapping.coverage_status,
        "rationale": mapping.rationale,
        "origin": mapping.origin,
    }


def _material_payload(material):
    return {
        "id": material.id,
        "stable_key": material.stable_key,
        "criterion_id": material.criterion_id,
        "section_id": material.section_id,
        "title": material.title,
        "material_status": material.material_status,
        "owner_name": material.owner_name,
        "notes": material.notes,
    }


def _material_summary(materials):
    return {
        status: sum(item.material_status == status for item in materials)
        for status in ("pending", "in_progress", "completed", "blocked")
    }


def _coverage_payload(criteria, mappings):
    confirmed_ids = {
        criterion.id
        for criterion in criteria
        if criterion.review_status == "confirmed"
    }
    mapped_ids = {
        mapping.criterion_id
        for mapping in mappings
        if mapping.coverage_status == "confirmed"
    }
    return {
        "confirmed": len(confirmed_ids & mapped_ids),
        "gap": len(confirmed_ids - mapped_ids),
        "proposed": sum(
            criterion.review_status == "suggested" for criterion in criteria
        ),
    }


def _workspace_payload(
    workspace,
    sections=None,
    criteria=None,
    sources=None,
    mappings=None,
    materials=None,
):
    criteria = criteria or []
    mappings = mappings or []
    materials = materials or []
    return {
        "id": workspace.id,
        "bid_file_id": workspace.bid_file_id,
        "title": workspace.title,
        "status": workspace.status,
        "revision": workspace.revision,
        "sections": [_section_payload(section) for section in (sections or [])],
        "source_references": [_source_payload(source) for source in (sources or [])],
        "criteria": [_criterion_payload(criterion) for criterion in criteria],
        "mappings": [_mapping_payload(mapping) for mapping in mappings],
        "coverage": _coverage_payload(criteria, mappings),
        "materials": [_material_payload(material) for material in materials],
        "material_summary": _material_summary(materials),
        "created_time": workspace.created_time.isoformat(),
        "updated_time": workspace.updated_time.isoformat(),
    }


def _get_workspace(db, workspace_id):
    workspace = db.query(BidWorkspace).filter(BidWorkspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=404,
            detail={"code": "WORKSPACE_NOT_FOUND", "message": "工作台不存在。"},
        )
    return workspace


def _get_sections(db, workspace_id):
    return (
        db.query(OutlineSection)
        .filter(OutlineSection.workspace_id == workspace_id)
        .order_by(OutlineSection.parent_id, OutlineSection.sort_order, OutlineSection.id)
        .all()
    )


def _get_criteria(db, workspace_id):
    return (
        db.query(ScoringCriterion)
        .filter(ScoringCriterion.workspace_id == workspace_id)
        .order_by(ScoringCriterion.id)
        .all()
    )


def _get_mappings(db, workspace_id):
    return (
        db.query(CriterionSectionMapping)
        .join(
            ScoringCriterion,
            CriterionSectionMapping.criterion_id == ScoringCriterion.id,
        )
        .filter(ScoringCriterion.workspace_id == workspace_id)
        .order_by(CriterionSectionMapping.id)
        .all()
    )


def _get_materials(db, workspace_id):
    return (
        db.query(ResponseMaterial)
        .filter(ResponseMaterial.workspace_id == workspace_id)
        .order_by(ResponseMaterial.id)
        .all()
    )


def _get_workspace_source_refs(db, sections, criteria):
    source_ids = {
        item.source_ref_id
        for item in [*sections, *criteria]
        if item.source_ref_id is not None
    }
    if not source_ids:
        return []
    return (
        db.query(SourceReference)
        .filter(SourceReference.id.in_(source_ids))
        .order_by(SourceReference.id)
        .all()
    )


def _loaded_workspace_payload(db, workspace):
    sections = _get_sections(db, workspace.id)
    criteria = _get_criteria(db, workspace.id)
    mappings = _get_mappings(db, workspace.id)
    materials = _get_materials(db, workspace.id)
    sources = _get_workspace_source_refs(db, sections, criteria)
    return _workspace_payload(workspace, sections, criteria, sources, mappings, materials)


def _snapshot(sections, criteria, mappings, materials):
    return json.dumps(
        {
            "sections": [_section_payload(section) for section in sections],
            "criteria": [_criterion_payload(criterion) for criterion in criteria],
            "mappings": [_mapping_payload(mapping) for mapping in mappings],
            "materials": [_material_payload(material) for material in materials],
        },
        ensure_ascii=False,
    )


def _claim_revision(db, workspace_id, expected_revision):
    next_revision = expected_revision + 1
    result = db.execute(
        update(BidWorkspace)
        .where(
            BidWorkspace.id == workspace_id,
            BidWorkspace.revision == expected_revision,
        )
        .values(revision=next_revision, updated_time=datetime.now())
    )
    if result.rowcount != 1:
        db.rollback()
        workspace = _get_workspace(db, workspace_id)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "WORKSPACE_REVISION_CONFLICT",
                "message": "工作台已被更新，请重新加载后再试。",
                "current_revision": workspace.revision,
            },
        )
    return next_revision


def _validate_parent(db, workspace_id, parent_id):
    if parent_id is None:
        return
    parent = db.query(OutlineSection).filter(OutlineSection.id == parent_id).first()
    if not parent or parent.workspace_id != workspace_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "SECTION_PARENT_INVALID", "message": "父级章节不属于当前工作台。"},
        )


def _validate_material_targets(db, workspace_id, criterion_id, section_id):
    if criterion_id is None and section_id is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "MATERIAL_TARGET_REQUIRED", "message": "响应材料至少需要关联一个评分点或章节。"},
        )
    if criterion_id is not None:
        criterion = db.query(ScoringCriterion).filter(ScoringCriterion.id == criterion_id).first()
        if not criterion or criterion.workspace_id != workspace_id:
            raise HTTPException(
                status_code=422,
                detail={"code": "MATERIAL_CRITERION_INVALID", "message": "评分点不属于当前工作台。"},
            )
        if criterion.review_status != "confirmed":
            raise HTTPException(
                status_code=409,
                detail={"code": "MATERIAL_CRITERION_UNCONFIRMED", "message": "只能关联已确认评分点。"},
            )
    if section_id is not None:
        section = db.query(OutlineSection).filter(OutlineSection.id == section_id).first()
        if not section or section.workspace_id != workspace_id:
            raise HTTPException(
                status_code=422,
                detail={"code": "MATERIAL_SECTION_INVALID", "message": "目录章节不属于当前工作台。"},
            )
        if section.review_status != "confirmed":
            raise HTTPException(
                status_code=409,
                detail={"code": "MATERIAL_SECTION_UNCONFIRMED", "message": "只能关联已确认目录章节。"},
            )


def _normalize_sibling_order(db, workspace_id, parent_id, ordered_sections):
    for index, section in enumerate(ordered_sections):
        section.parent_id = parent_id
        section.sort_order = index


def _save_revision(db, workspace_id, revision, action):
    sections = _get_sections(db, workspace_id)
    criteria = _get_criteria(db, workspace_id)
    mappings = _get_mappings(db, workspace_id)
    materials = _get_materials(db, workspace_id)
    db.add(
        WorkspaceRevision(
            workspace_id=workspace_id,
            revision=revision,
            action=action,
            snapshot=_snapshot(sections, criteria, mappings, materials),
        )
    )
    return sections, criteria


def _compact_text(value):
    return re.sub(r"\s+", "", value or "")


def _validated_suggestions(result, pages):
    page_text = {
        item.get("page"): _compact_text(item.get("text"))
        for item in pages
        if isinstance(item, dict)
    }
    valid = []
    valid_indices = set()
    warnings = []
    for index, item in enumerate(result.get("suggestions", [])):
        if not isinstance(item, dict):
            warnings.append({"index": index, "code": "SUGGESTION_INVALID"})
            continue
        title = str(item.get("title") or "").strip()
        quote = str(item.get("quote") or "").strip()
        page = item.get("page")
        parent_index = item.get("parent_index")
        normalized_quote = _compact_text(quote)
        parent_valid = parent_index is None or (
            isinstance(parent_index, int)
            and not isinstance(parent_index, bool)
            and 0 <= parent_index < index
            and parent_index in valid_indices
        )
        if (
            not title
            or len(title) > 200
            or not isinstance(page, int)
            or isinstance(page, bool)
            or not normalized_quote
            or normalized_quote not in page_text.get(page, "")
            or not parent_valid
        ):
            warnings.append({"index": index, "code": "SOURCE_NOT_VERIFIED"})
            continue
        valid.append(
            {
                "original_index": index,
                "title": title,
                "page": page,
                "quote": quote,
                "parent_index": parent_index,
            }
        )
        valid_indices.add(index)
    if not valid:
        raise AIResponseFormatError("AI outline response has no source-backed suggestions")
    return valid, warnings


def _validated_criteria(result, pages):
    page_text = {
        item.get("page"): _compact_text(item.get("text"))
        for item in pages
        if isinstance(item, dict)
    }
    valid = []
    warnings = []
    for index, item in enumerate(result.get("criteria", [])):
        if not isinstance(item, dict):
            warnings.append({"index": index, "code": "CRITERION_INVALID"})
            continue
        title = str(item.get("title") or "").strip()
        requirement = str(item.get("requirement") or "").strip()
        quote = str(item.get("quote") or "").strip()
        page = item.get("page")
        raw_score = item.get("max_score")
        score = None
        score_valid = raw_score is None
        if raw_score is not None and not isinstance(raw_score, bool):
            try:
                score = Decimal(str(raw_score))
                score_valid = score.is_finite() and score >= 0
            except (InvalidOperation, ValueError):
                score_valid = False
        normalized_quote = _compact_text(quote)
        if (
            not title
            or len(title) > 200
            or not requirement
            or len(requirement) > 4000
            or not isinstance(page, int)
            or isinstance(page, bool)
            or not normalized_quote
            or normalized_quote not in page_text.get(page, "")
            or not score_valid
        ):
            warnings.append({"index": index, "code": "CRITERION_SOURCE_NOT_VERIFIED"})
            continue
        valid.append(
            {
                "title": title,
                "requirement": requirement,
                "max_score": score,
                "page": page,
                "quote": quote,
            }
        )
    if not valid:
        raise AIResponseFormatError("AI criteria response has no source-backed criteria")
    return valid, warnings


@router.post("/workspaces")
def create_workspace(payload: WorkspaceCreate):
    db = SessionLocal()
    try:
        bid_file = db.query(BidFile).filter(BidFile.id == payload.bid_file_id).first()
        if not bid_file:
            raise HTTPException(
                status_code=404,
                detail={"code": "BID_FILE_NOT_FOUND", "message": "项目不存在。"},
            )

        existing = (
            db.query(BidWorkspace)
            .filter(BidWorkspace.bid_file_id == payload.bid_file_id)
            .first()
        )
        if existing:
            return _loaded_workspace_payload(db, existing)

        requested_title = (payload.title or "").strip()
        title = requested_title or bid_file.project_name or bid_file.filename or "未命名项目"
        workspace = BidWorkspace(bid_file_id=bid_file.id, title=title)
        db.add(workspace)
        db.flush()
        db.add(
            WorkspaceRevision(
                workspace_id=workspace.id,
                revision=1,
                action="create",
                snapshot=json.dumps(
                    {"sections": [], "criteria": [], "mappings": [], "materials": []},
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        db.refresh(workspace)
        return _workspace_payload(workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "WORKSPACE_CREATE_FAILED", "message": "工作台创建失败。"},
        ) from exc
    finally:
        db.close()


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: int):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        return _loaded_workspace_payload(db, workspace)
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/sections")
def create_section(workspace_id: int, payload: SectionCreate):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        _validate_parent(db, workspace_id, payload.parent_id)
        revision = _claim_revision(db, workspace_id, payload.revision)
        siblings = (
            db.query(OutlineSection)
            .filter(
                OutlineSection.workspace_id == workspace_id,
                OutlineSection.parent_id == payload.parent_id,
            )
            .order_by(OutlineSection.sort_order, OutlineSection.id)
            .all()
        )
        title = payload.title.strip()
        if not title:
            raise HTTPException(
                status_code=422,
                detail={"code": "SECTION_TITLE_REQUIRED", "message": "章节标题不能为空。"},
            )
        section = OutlineSection(
            workspace_id=workspace_id,
            parent_id=payload.parent_id,
            stable_key=f"manual-{uuid4().hex}",
            title=title,
            sort_order=len(siblings),
            origin="user",
            review_status="confirmed",
        )
        db.add(section)
        db.flush()
        sections, criteria = _save_revision(db, workspace_id, revision, "section_create")
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "SECTION_CREATE_FAILED", "message": "章节创建失败。"},
        ) from exc
    finally:
        db.close()


@router.patch("/workspaces/{workspace_id}/sections/{section_id}")
def update_section(workspace_id: int, section_id: int, payload: SectionUpdate):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        section = db.query(OutlineSection).filter(OutlineSection.id == section_id).first()
        if not section or section.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "SECTION_NOT_FOUND", "message": "章节不存在。"},
            )
        if payload.title is None and payload.sort_order is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "SECTION_UPDATE_EMPTY", "message": "没有可更新的章节字段。"},
            )
        revision = _claim_revision(db, workspace_id, payload.revision)
        action = "section_update"
        if payload.title is not None:
            title = payload.title.strip()
            if not title:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "SECTION_TITLE_REQUIRED", "message": "章节标题不能为空。"},
                )
            section.title = title
        if payload.sort_order is not None:
            siblings = (
                db.query(OutlineSection)
                .filter(
                    OutlineSection.workspace_id == workspace_id,
                    OutlineSection.parent_id == section.parent_id,
                    OutlineSection.id != section.id,
                )
                .order_by(OutlineSection.sort_order, OutlineSection.id)
                .all()
            )
            target = min(payload.sort_order, len(siblings))
            siblings.insert(target, section)
            _normalize_sibling_order(db, workspace_id, section.parent_id, siblings)
            action = "section_reorder" if payload.title is None else "section_update"
        db.flush()
        sections, criteria = _save_revision(db, workspace_id, revision, action)
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "SECTION_UPDATE_FAILED", "message": "章节更新失败。"},
        ) from exc
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/outline-suggestions")
def create_outline_suggestions(workspace_id: int, payload: OutlineSuggestionCreate):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        bid_file = db.query(BidFile).filter(BidFile.id == workspace.bid_file_id).first()
        try:
            source_path = resolve_upload_file(bid_file.filepath, require_file=True)
            pages = parse_document(str(source_path))
        except UnsafeStoragePathError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "UNSAFE_STORED_PATH", "message": "历史文件路径不安全，已阻止访问。"},
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail={"code": "SOURCE_FILE_NOT_FOUND", "message": "招标源文件不存在。"},
            ) from exc
        except DocumentParseError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "SOURCE_PARSE_FAILED", "message": "招标源文件无法解析。"},
            ) from exc

        try:
            result = generate_outline_suggestions(pages)
            suggestions, warnings = _validated_suggestions(result, pages)
        except Exception as exc:
            raise to_ai_http_exception(exc) from exc

        revision = _claim_revision(db, workspace_id, payload.revision)
        sections_by_source_index = {}
        sibling_counts = {}
        for existing in _get_sections(db, workspace_id):
            sibling_counts[existing.parent_id] = max(
                sibling_counts.get(existing.parent_id, 0),
                existing.sort_order + 1,
            )
        for suggestion in suggestions:
            parent = sections_by_source_index.get(suggestion["parent_index"])
            parent_id = parent.id if parent else None
            source_ref = SourceReference(
                bid_file_id=workspace.bid_file_id,
                page=suggestion["page"],
                quote=suggestion["quote"],
                locator=json.dumps({"page": suggestion["page"]}, ensure_ascii=False),
                fingerprint=hashlib.sha256(
                    f"{workspace.bid_file_id}:{suggestion['page']}:{_compact_text(suggestion['quote'])}".encode("utf-8")
                ).hexdigest(),
            )
            db.add(source_ref)
            db.flush()
            sort_order = sibling_counts.get(parent_id, 0)
            sibling_counts[parent_id] = sort_order + 1
            section = OutlineSection(
                workspace_id=workspace_id,
                parent_id=parent_id,
                stable_key=f"ai-{uuid4().hex}",
                title=suggestion["title"],
                sort_order=sort_order,
                origin="ai",
                review_status="suggested",
                source_ref_id=source_ref.id,
            )
            db.add(section)
            db.flush()
            sections_by_source_index[suggestion["original_index"]] = section
        sections, criteria = _save_revision(
            db, workspace_id, revision, "outline_suggestions"
        )
        db.commit()
        db.refresh(workspace)
        response = _loaded_workspace_payload(db, workspace)
        response["warnings"] = warnings
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "OUTLINE_SUGGESTION_FAILED", "message": "目录建议生成失败。"},
        ) from exc
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/criteria-extractions")
def create_criteria_extraction(workspace_id: int, payload: CriteriaExtractionCreate):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        bid_file = db.query(BidFile).filter(BidFile.id == workspace.bid_file_id).first()
        try:
            source_path = resolve_upload_file(bid_file.filepath, require_file=True)
            pages = parse_document(str(source_path))
        except UnsafeStoragePathError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "UNSAFE_STORED_PATH", "message": "历史文件路径不安全，已阻止访问。"},
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail={"code": "SOURCE_FILE_NOT_FOUND", "message": "招标源文件不存在。"},
            ) from exc
        except DocumentParseError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "SOURCE_PARSE_FAILED", "message": "招标源文件无法解析。"},
            ) from exc

        try:
            result = generate_scoring_criteria(pages)
            extracted, warnings = _validated_criteria(result, pages)
        except Exception as exc:
            raise to_ai_http_exception(exc) from exc

        revision = _claim_revision(db, workspace_id, payload.revision)
        for item in extracted:
            source_ref = SourceReference(
                bid_file_id=workspace.bid_file_id,
                page=item["page"],
                quote=item["quote"],
                locator=json.dumps({"page": item["page"]}, ensure_ascii=False),
                fingerprint=hashlib.sha256(
                    f"{workspace.bid_file_id}:{item['page']}:{_compact_text(item['quote'])}".encode("utf-8")
                ).hexdigest(),
            )
            db.add(source_ref)
            db.flush()
            db.add(
                ScoringCriterion(
                    workspace_id=workspace_id,
                    stable_key=f"ai-{uuid4().hex}",
                    title=item["title"],
                    requirement=item["requirement"],
                    max_score=item["max_score"],
                    review_status="suggested",
                    source_ref_id=source_ref.id,
                )
            )
        db.flush()
        sections, criteria = _save_revision(
            db, workspace_id, revision, "criteria_extraction"
        )
        db.commit()
        db.refresh(workspace)
        response = _loaded_workspace_payload(db, workspace)
        response["warnings"] = warnings
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "CRITERIA_EXTRACTION_FAILED", "message": "评分点提取失败。"},
        ) from exc
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/sections/{section_id}/review")
def review_section_suggestion(
    workspace_id: int,
    section_id: int,
    payload: SectionReviewUpdate,
):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        section = db.query(OutlineSection).filter(OutlineSection.id == section_id).first()
        if not section or section.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "SECTION_NOT_FOUND", "message": "章节不存在。"},
            )
        if section.origin != "ai" or section.review_status != "suggested":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SECTION_REVIEW_NOT_PENDING",
                    "message": "该章节不是待审核的AI建议。",
                },
            )
        revision = _claim_revision(db, workspace_id, payload.revision)
        if payload.decision == "accept":
            section.review_status = "confirmed"
            action = "section_suggestion_accept"
        else:
            section.review_status = "rejected"
            action = "section_suggestion_reject"
        db.flush()
        sections, criteria = _save_revision(db, workspace_id, revision, action)
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "SECTION_REVIEW_FAILED", "message": "目录建议审核失败。"},
        ) from exc
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/criteria/{criterion_id}/review")
def review_scoring_criterion(
    workspace_id: int,
    criterion_id: int,
    payload: SectionReviewUpdate,
):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        criterion = (
            db.query(ScoringCriterion)
            .filter(ScoringCriterion.id == criterion_id)
            .first()
        )
        if not criterion or criterion.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "CRITERION_NOT_FOUND", "message": "评分点不存在。"},
            )
        if criterion.review_status != "suggested":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CRITERION_REVIEW_NOT_PENDING",
                    "message": "该评分点不是待审核建议。",
                },
            )
        revision = _claim_revision(db, workspace_id, payload.revision)
        if payload.decision == "accept":
            criterion.review_status = "confirmed"
            action = "criterion_suggestion_accept"
        else:
            criterion.review_status = "rejected"
            action = "criterion_suggestion_reject"
        db.flush()
        sections, criteria = _save_revision(db, workspace_id, revision, action)
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "CRITERION_REVIEW_FAILED", "message": "评分点审核失败。"},
        ) from exc
    finally:
        db.close()


@router.put("/workspaces/{workspace_id}/mappings")
def upsert_criterion_mappings(workspace_id: int, payload: MappingUpsert):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        requested_pairs = [
            (item.criterion_id, item.section_id) for item in payload.mappings
        ]
        if len(requested_pairs) != len(set(requested_pairs)):
            raise HTTPException(
                status_code=422,
                detail={"code": "MAPPING_DUPLICATE", "message": "映射列表包含重复关系。"},
            )

        criterion_ids = {item.criterion_id for item in payload.mappings}
        section_ids = {item.section_id for item in payload.mappings}
        criteria = {
            item.id: item
            for item in db.query(ScoringCriterion)
            .filter(ScoringCriterion.id.in_(criterion_ids))
            .all()
        }
        sections = {
            item.id: item
            for item in db.query(OutlineSection)
            .filter(OutlineSection.id.in_(section_ids))
            .all()
        }
        for item in payload.mappings:
            criterion = criteria.get(item.criterion_id)
            section = sections.get(item.section_id)
            if not criterion or criterion.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "MAPPING_CRITERION_INVALID",
                        "message": "评分点不属于当前工作台。",
                    },
                )
            if criterion.review_status != "confirmed":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "MAPPING_CRITERION_UNCONFIRMED",
                        "message": "只能映射已确认评分点。",
                    },
                )
            if not section or section.workspace_id != workspace_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "MAPPING_SECTION_INVALID",
                        "message": "目录章节不属于当前工作台。",
                    },
                )
            if section.review_status != "confirmed":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "MAPPING_SECTION_UNCONFIRMED",
                        "message": "只能映射已确认目录章节。",
                    },
                )

        revision = _claim_revision(db, workspace_id, payload.revision)
        for item in payload.mappings:
            mapping = (
                db.query(CriterionSectionMapping)
                .filter(
                    CriterionSectionMapping.criterion_id == item.criterion_id,
                    CriterionSectionMapping.section_id == item.section_id,
                )
                .first()
            )
            rationale = (item.rationale or "").strip() or None
            if mapping:
                mapping.rationale = rationale
                mapping.coverage_status = "confirmed"
                mapping.origin = "user"
            else:
                db.add(
                    CriterionSectionMapping(
                        criterion_id=item.criterion_id,
                        section_id=item.section_id,
                        coverage_status="confirmed",
                        rationale=rationale,
                        origin="user",
                    )
                )
        db.flush()
        _save_revision(db, workspace_id, revision, "mappings_upsert")
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "MAPPING_SAVE_FAILED", "message": "评分点映射保存失败。"},
        ) from exc
    finally:
        db.close()


@router.get("/workspaces/{workspace_id}/materials")
def list_response_materials(workspace_id: int):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        materials = _get_materials(db, workspace_id)
        return {
            "items": [_material_payload(material) for material in materials],
            "summary": _material_summary(materials),
            "revision": workspace.revision,
        }
    finally:
        db.close()


@router.post("/workspaces/{workspace_id}/materials")
def create_response_material(workspace_id: int, payload: MaterialCreate):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        title = payload.title.strip()
        if not title:
            raise HTTPException(
                status_code=422,
                detail={"code": "MATERIAL_TITLE_REQUIRED", "message": "材料标题不能为空。"},
            )
        _validate_material_targets(db, workspace_id, payload.criterion_id, payload.section_id)
        revision = _claim_revision(db, workspace_id, payload.revision)
        db.add(
            ResponseMaterial(
                workspace_id=workspace_id,
                criterion_id=payload.criterion_id,
                section_id=payload.section_id,
                stable_key=f"material-{uuid4().hex}",
                title=title,
                material_status=payload.material_status,
                owner_name=(payload.owner_name or "").strip() or None,
                notes=(payload.notes or "").strip() or None,
            )
        )
        db.flush()
        _save_revision(db, workspace_id, revision, "material_create")
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "MATERIAL_CREATE_FAILED", "message": "响应材料创建失败。"},
        ) from exc
    finally:
        db.close()


@router.patch("/workspaces/{workspace_id}/materials/{material_id}")
def update_response_material(workspace_id: int, material_id: int, payload: MaterialUpdate):
    db = SessionLocal()
    try:
        workspace = _get_workspace(db, workspace_id)
        material = db.query(ResponseMaterial).filter(ResponseMaterial.id == material_id).first()
        if not material or material.workspace_id != workspace_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "MATERIAL_NOT_FOUND", "message": "响应材料不存在。"},
            )
        update_fields = payload.model_fields_set - {"revision"}
        if not update_fields:
            raise HTTPException(
                status_code=422,
                detail={"code": "MATERIAL_UPDATE_EMPTY", "message": "没有可更新的材料字段。"},
            )
        if "title" in update_fields:
            title = (payload.title or "").strip()
            if not title:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "MATERIAL_TITLE_REQUIRED", "message": "材料标题不能为空。"},
                )
            material.title = title
        if "material_status" in update_fields and payload.material_status is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "MATERIAL_STATUS_REQUIRED", "message": "材料状态不能为空。"},
            )
        revision = _claim_revision(db, workspace_id, payload.revision)
        if "material_status" in update_fields:
            material.material_status = payload.material_status
        if "owner_name" in update_fields:
            material.owner_name = (payload.owner_name or "").strip() or None
        if "notes" in update_fields:
            material.notes = (payload.notes or "").strip() or None
        db.flush()
        _save_revision(db, workspace_id, revision, "material_update")
        db.commit()
        db.refresh(workspace)
        return _loaded_workspace_payload(db, workspace)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "MATERIAL_UPDATE_FAILED", "message": "响应材料更新失败。"},
        ) from exc
    finally:
        db.close()
