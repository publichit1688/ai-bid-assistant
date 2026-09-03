from sqlalchemy import Column, String, Integer, Text, DateTime

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