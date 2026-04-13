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
from api.diet_article import router as diet_article_router
from api.coach_diet_article import router as coach_diet_article_router
from api.admin_diet_article import router as admin_diet_article_router
from api.course import router as course_router
from api.coach_course import router as coach_course_router
from api.admin_course import router as admin_course_router
from api.diet_record import router as diet_record_router
from api.coach_food import router as coach_food_router
from api.admin_food import router as admin_food_router
from api.training import router as training_router
from api.coach_training import router as coach_training_router
from api.coach_bind import router as coach_bind_router
from api.coach_profile import router as coach_profile_router
from api.diet_plan import router as diet_plan_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时：自动建表 → 初始化超级管理员（幂等）"""
    async with engine.begin() as conn:
        import models  # 触发所有 ORM 模型注册到 Base
        await conn.run_sync(Base.metadata.create_all)

    # 建表完成后检查并创建管理员账号
    from db.session import AsyncSessionLocal
    from CRUD.user import ensure_admin_exists
    from CRUD.diet_record import ensure_foods
    async with AsyncSessionLocal() as db:
        await ensure_admin_exists(db)
        await ensure_foods(db)  # 写入系统预置食物（幂等）

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
app.include_router(diet_article_router, prefix="/api")       # 用户端：GET /diet/articles
app.include_router(coach_diet_article_router, prefix="/api") # 教练端：/coach/diet/articles
app.include_router(admin_diet_article_router, prefix="/api") # 管理员：/admin/diet/articles
app.include_router(course_router, prefix="/api")             # 用户端：/courses
app.include_router(coach_course_router, prefix="/api")       # 教练端：/coach/courses
app.include_router(admin_course_router, prefix="/api")       # 管理员：/admin/courses
app.include_router(diet_record_router, prefix="/api")        # 饮食记录：/diet/foods/search  /diet/records
app.include_router(coach_food_router, prefix="/api")         # 教练端食物投稿：/coach/foods
app.include_router(admin_food_router, prefix="/api")         # 管理员食物审核：/admin/foods
app.include_router(training_router, prefix="/api")           # 用户训练模块：/training/records /training/plans /training/stats
app.include_router(coach_training_router, prefix="/api")     # 教练训练模块：/coach/students /coach/training/plans
app.include_router(coach_bind_router, prefix="/api")         # 教练-学员绑定：/coaches /coach-bind /coach/bind-requests /admin/coach-bind
app.include_router(coach_profile_router, prefix="/api")      # 教练主页：/coach/profile  /coaches/{id}
app.include_router(diet_plan_router, prefix="/api")          # 饮食计划：/coach/diet-plans  /diet-plans
