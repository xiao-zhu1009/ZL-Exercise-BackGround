# api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from db.session import get_db
from models.user import User
from schemas.user import LoginForm, RegisterForm, SendCodeForm, VerifyCodeForm
from utils.jwt import create_access_token
from utils.response import success

router = APIRouter(prefix="/auth", tags=["auth"])

# 写死的验证码（后续改为真实短信）
FAKE_CODE = "123456"


@router.get("/")
async def root():
    return {"message": "Hello World"}


# 登录
@router.post("/login")
async def login(form: LoginForm, db: AsyncSession = Depends(get_db)):
    # 支持账号或手机号登录
    result = await db.execute(
        select(User).where(or_(User.username == form.account, User.phone == form.account))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="账号/手机号不存在")
    if user.password != form.password:
        raise HTTPException(status_code=401, detail="密码错误")

    token = create_access_token({"user_id": user.id, "role": user.role})
    return success({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "nickname": user.nickname,
        "token": token
    }, "登录成功")

# 发送验证码
@router.post("/send-code")
async def send_code(form: SendCodeForm):
    return success(None, "验证码已发送（测试码：123456）")

# 验证验证码
@router.post("/verify-code")
async def verify_code(form: VerifyCodeForm):
    if form.code != FAKE_CODE:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    return success(None, "验证通过")

# 注册
@router.post("/register")
async def register(form: RegisterForm, db: AsyncSession = Depends(get_db)):
    # 检查验证码
    if form.code != FAKE_CODE:
        raise HTTPException(status_code=400, detail="请先完成手机验证")

    # 检查账号/手机号是否重复
    result = await db.execute(
        select(User).where(or_(User.username == form.username, User.phone == form.phone))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="账号或手机号已存在")

    user = User(
        username=form.username,
        password=form.password,
        nickname=form.nickname,
        phone=form.phone
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return success({"id": user.id, "username": user.username}, "注册成功")
