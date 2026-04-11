# main.py
# 应用入口：创建 FastAPI 实例，注册中间件，挂载路由，启动时建表

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from db.session import engine, Base
from utils.exception_handlers import http_exception_handler, validation_exception_handler
from api.auth import router as auth_router
from api.test import router as test_router
from api.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动建表（表已存在则跳过）"""
    async with engine.begin() as conn:
        import models  # 触发所有 ORM 模型注册到 Base
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由，统一前缀 /ZL-API
app.include_router(auth_router, prefix="/api")
app.include_router(test_router, prefix="/api")
app.include_router(user_router, prefix="/api")
