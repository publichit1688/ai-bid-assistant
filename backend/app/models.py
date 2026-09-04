from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint

from datetime import datetime

from app.database import Base



class BidFile(Base):

    __tablename__ = "bid_files"



    id = Column(
        Integer,
        primary_key=True,
        index=True
    )



    filename = Column(
        String
    )



    filepath = Column(
        String
    )



    # 项目名称
    project_name = Column(
        String,
        nullable=True
    )



    # AI评分
    score = Column(
        Integer,
        default=0
    )



    # 风险数量
    risk_count = Column(
        Integer,
        default=0
    )



    # AI完整分析结果
    analysis = Column(
        Text,
        nullable=True
    )



    # 风险定位信息
    risk = Column(
        Text,
        nullable=True
    )



    status = Column(
        String,
        default="uploaded"
    )



    # 创建时间
    created_time = Column(
        DateTime,
        default=datetime.now
    )



# ==================================
# Dashboard V2.5.3
# AI管理摘要持久化缓存
# ==================================

class DashboardAICache(Base):

    __tablename__ = "dashboard_ai_cache"


    # 主键
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    # Dashboard数据指纹
    fingerprint = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )


    # 统计周期
    # 例如：7天 / 30天
    days = Column(
        Integer,
        nullable=False
    )


    # AI管理摘要
    # 保存完整JSON字符串
    summary = Column(
        Text,
        nullable=False
    )


    # 缓存创建时间
    created_time = Column(
        DateTime,
        default=datetime.now
    )


class BidWorkspace(Base):
    __tablename__ = "bid_workspaces"

    id = Column(Integer, primary_key=True, index=True)
    bid_file_id = Column(Integer, ForeignKey("bid_files.id"), unique=True, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")
    revision = Column(Integer, nullable=False, default=1)
    created_time = Column(DateTime, nullable=False, default=datetime.now)
    updated_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class SourceReference(Base):
    __tablename__ = "source_references"

    id = Column(Integer, primary_key=True, index=True)
    bid_file_id = Column(Integer, ForeignKey("bid_files.id"), nullable=False, index=True)
    page = Column(Integer, nullable=True)
    quote = Column(Text, nullable=False)
    locator = Column(Text, nullable=True)
    fingerprint = Column(String, nullable=False, index=True)


class OutlineSection(Base):
    __tablename__ = "outline_sections"
    __table_args__ = (
        UniqueConstraint("workspace_id", "stable_key", name="uq_outline_workspace_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("bid_workspaces.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("outline_sections.id"), nullable=True)
    stable_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False)
    origin = Column(String, nullable=False)
    review_status = Column(String, nullable=False)
    source_ref_id = Column(Integer, ForeignKey("source_references.id"), nullable=True)
    created_time = Column(DateTime, nullable=False, default=datetime.now)
    updated_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class ScoringCriterion(Base):
    __tablename__ = "scoring_criteria"
    __table_args__ = (
        UniqueConstraint("workspace_id", "stable_key", name="uq_criterion_workspace_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("bid_workspaces.id"), nullable=False, index=True)
    stable_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    requirement = Column(Text, nullable=False)
    max_score = Column(Numeric, nullable=True)
    review_status = Column(String, nullable=False)
    source_ref_id = Column(Integer, ForeignKey("source_references.id"), nullable=False)
    created_time = Column(DateTime, nullable=False, default=datetime.now)
    updated_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class CriterionSectionMapping(Base):
    __tablename__ = "criterion_section_mappings"
    __table_args__ = (
        UniqueConstraint("criterion_id", "section_id", name="uq_criterion_section"),
    )

    id = Column(Integer, primary_key=True, index=True)
    criterion_id = Column(Integer, ForeignKey("scoring_criteria.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("outline_sections.id"), nullable=False, index=True)
    coverage_status = Column(String, nullable=False)
    rationale = Column(Text, nullable=True)
    origin = Column(String, nullable=False)
    created_time = Column(DateTime, nullable=False, default=datetime.now)
    updated_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class ResponseMaterial(Base):
    __tablename__ = "response_materials"
    __table_args__ = (
        UniqueConstraint("workspace_id", "stable_key", name="uq_material_workspace_key"),
        CheckConstraint(
            "criterion_id IS NOT NULL OR section_id IS NOT NULL",
            name="ck_material_target",
        ),
        CheckConstraint(
            "material_status IN ('pending', 'in_progress', 'completed', 'blocked')",
            name="ck_material_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("bid_workspaces.id"), nullable=False, index=True)
    criterion_id = Column(Integer, ForeignKey("scoring_criteria.id"), nullable=True, index=True)
    section_id = Column(Integer, ForeignKey("outline_sections.id"), nullable=True, index=True)
    stable_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    material_status = Column(String, nullable=False, default="pending")
    owner_name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_time = Column(DateTime, nullable=False, default=datetime.now)
    updated_time = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class WorkspaceRevision(Base):
    __tablename__ = "workspace_revisions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "revision", name="uq_workspace_revision"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("bid_workspaces.id"), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    snapshot = Column(Text, nullable=False)
    created_time = Column(DateTime, nullable=False, default=datetime.now)
