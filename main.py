# main.py
# 应用入口：创建 FastAPI 实例，注册中间件，挂载路由，启动时建表

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from db.session import engine, Base
from utils.exception_handlers import http_exception_handler, validation_exception_handler
from api.auth import router as auth_router
from api.test import router as test_router
from api.user import router as user_router
from api.action import router as action_router
from api.coach_action import router as coach_action_router
from api.admin_action import router as admin_action_router
from api.coach_application import router as coach_application_router
from api.admin_user import router as admin_user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时：自动建表 → 初始化超级管理员（幂等）"""
    async with engine.begin() as conn:
        import models  # 触发所有 ORM 模型注册到 Base
        await conn.run_sync(Base.metadata.create_all)

    # 建表完成后检查并创建管理员账号
    from db.session import AsyncSessionLocal
    from CRUD.user import ensure_admin_exists
    async with AsyncSessionLocal() as db:
        await ensure_admin_exists(db)

    yield


app = FastAPI(lifespan=lifespan)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 用户上传头像等静态资源（URL: /api/static/...）
app.mount("/api/static", StaticFiles(directory="static"), name="static")

# 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由，统一前缀 /api
# 动作库三个路由对应三个角色：公开只读 / 教练投稿 / 管理员审核
app.include_router(auth_router, prefix="/api")
app.include_router(test_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(action_router, prefix="/api")        # 用户端：GET /actions
app.include_router(coach_action_router, prefix="/api")  # 教练端：/coach/actions
app.include_router(admin_action_router, prefix="/api")  # 管理员：/admin/actions
app.include_router(coach_application_router, prefix="/api")  # 教练申请
app.include_router(admin_user_router, prefix="/api")         # 超管用户管理
