# main.py
# 职责：应用入口 —— 创建 FastAPI 实例，注册中间件和路由，启动时建表
# 依赖：
#   - db/session.py  → engine + Base（启动时用 Base.metadata.create_all 建表）
#   - api/auth.py    → auth_router（挂载登录/注册路由）
#
# 启动流程：
#   uvicorn 启动 → lifespan 执行建表 → 注册 CORS 中间件 → 挂载路由
#   → 开始接收请求

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from db.session import engine, Base
from api.auth import router as auth_router
from api.test import router as test_router

# lifespan：替代旧版 @app.on_event("startup")，在应用启动/关闭时执行
# create_all：根据所有继承 Base 的 ORM 模型自动建表（表已存在则跳过）
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # 注意：models 必须在这里之前被 import，否则 Base 不知道有哪些表
        import models  # noqa: F401 —— 触发所有模型注册到 Base
        await conn.run_sync(Base.metadata.create_all)
    yield  # yield 之后的代码在应用关闭时执行（此处无需清理）

app = FastAPI(lifespan=lifespan)

# CORS：允许前端开发服务器（localhost:8080）跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由，prefix 已在各 router 内定义（如 /auth）
app.include_router(auth_router, prefix="/ZL-API")
app.include_router(test_router, prefix="/ZL-API")
