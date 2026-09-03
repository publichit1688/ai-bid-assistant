from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_cors_origins, get_report_dir, get_upload_dir
from app.services.auth import SharedTokenAuthMiddleware, auth_is_enabled
from app.services.request_logging import RequestLoggingMiddleware
from app.services.rate_limit import RateLimitMiddleware
from app.version import APP_VERSION

# 数据库

from app.database import engine, Base

# 重要：加载所有数据库模型
from app.models import BidFile



# API接口

from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.files import router as files_router
from app.api.compare import router as compare_router
from app.api.dashboard import router as dashboard_router
from app.api import report
from app.api import compare_report



# =========================
# 创建数据库表
# =========================

Base.metadata.create_all(
    bind=engine
)

upload_dir = get_upload_dir()
upload_dir.mkdir(parents=True, exist_ok=True)
get_report_dir().mkdir(parents=True, exist_ok=True)





# =========================
# 创建 FastAPI
# =========================

app = FastAPI(

    title="AI Bid Assistant",

    version=APP_VERSION,

    docs_url=None if auth_is_enabled() else "/docs",

    redoc_url=None if auth_is_enabled() else "/redoc",

    openapi_url=None if auth_is_enabled() else "/openapi.json",

)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SharedTokenAuthMiddleware)
app.add_middleware(RequestLoggingMiddleware)





# =========================
# 开放 uploads 文件夹
# 用于PDF在线预览
# =========================

app.mount(

    "/uploads",

    StaticFiles(
        directory=str(upload_dir)
    ),

    name="uploads"

)







# =========================
# CORS
# 允许 React 前端访问
# =========================

app.add_middleware(

    CORSMiddleware,


    allow_origins=get_cors_origins(),


    allow_credentials=True,


    allow_methods=["*"],


    allow_headers=["*"]

)








# =========================
# 注册路由
# =========================


# 健康检查

app.include_router(

    health_router,

    prefix="/api"

)

app.include_router(
    compare_report.router,
    prefix="/api"
)

app.include_router(
    compare_router,
    prefix="/api"
)

app.include_router(
    dashboard_router,
    prefix="/api"
)



# 上传分析

app.include_router(

    upload_router,

    prefix="/api"

)





# 历史文件

app.include_router(

    files_router,

    prefix="/api"

)




app.include_router(
    report.router,
    prefix="/api"
)






# =========================
# 首页测试
# =========================

@app.get("/")

def root():

    return {

        "message":

        "Hello AI Bid Assistant"

    }
