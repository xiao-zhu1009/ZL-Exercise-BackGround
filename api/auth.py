# api/auth.py
# 职责：登录、注册接口路由
# 依赖：
#   - db/session.py     → get_db（获取数据库会话）
#   - models/user.py    → User（ORM 模型，操作 users 表）
#   - schemas/user.py   → LoginForm、RegisterForm（请求体校验）
#   - utils/jwt.py      → create_access_token（登录成功后签发 Token）
#   - utils/response.py → success / fail（统一响应格式）
#
# 业务流向（登录）：
#   POST /auth/login → 校验请求体 → 查数据库 → 验证密码哈希
#   → 签发 JWT Token → 返回用户信息 + Token
#
# 业务流向（注册）：
#   POST /auth/register → 校验请求体 → 检查用户名是否重复
#   → 哈希密码 → 插入数据库 → 返回新用户信息

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models.user import User
from schemas.user import LoginForm, RegisterForm
from utils.jwt import create_access_token
from utils.response import success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/")
async def root():
    return {"message": "Hello World"}
# 登录接口
@router.post("/login")
async def login(form: LoginForm, db: AsyncSession = Depends(get_db)):
    # 1. 按用户名查询（scalar_one_or_none：找不到返回 None，不抛异常）
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    # 2. 用户不存在 或 密码不匹配
    if not user or user.password != form.password:
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    # 3. 签发 JWT，payload 里存 user_id 和 role，后续受保护接口可从 Token 里取
    token = create_access_token({"user_id": user.id, "role": user.role})
    print(token)
    return success({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "nickname": user.nickname,
        "token": token
    }, "登录成功")


@router.post("/register")
async def register(form: RegisterForm, db: AsyncSession = Depends(get_db)):
    print("触发注册接口333333333333333333")
    # 1. 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == form.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 2. 哈希密码后写入数据库（绝不存明文）
    user = User(
        username=form.username,
        password=form.password,
        nickname=form.nickname
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)  # refresh：从数据库重新读取，拿到自增 id 等字段

    return success({"id": user.id, "username": user.username}, "注册成功")
