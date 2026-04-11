# api/auth.py
# 认证路由：登录、注册、验证码

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.user import LoginForm, RegisterForm, SendCodeForm, VerifyCodeForm
from utils.jwt import create_access_token
from utils.response import success, json_fail
from CRUD.user import (
    get_user_by_account,
    check_user_exists,
    create_user,
    save_user_token,
    is_phone_registered,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# 测试用验证码，后续替换为真实短信服务
FAKE_CODE = "123456"


@router.post("/login")
async def login(form: LoginForm, db: AsyncSession = Depends(get_db)):
    """登录：支持账号或手机号"""
    user = await get_user_by_account(db, form.account)
    if not user:
        return json_fail("账号未注册", 401)
    if user.password != form.password:
        return json_fail("密码错误", 401)

    token = create_access_token({"user_id": user.id, "role": user.role})
    await save_user_token(db, user, token)

    return success({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "nickname": user.nickname,
        "token": token
    }, "登录成功")


@router.post("/send-code")
async def send_code(form: SendCodeForm, db: AsyncSession = Depends(get_db)):
    """发送验证码（当前为测试模式，固定返回 123456）"""
    if await is_phone_registered(db, form.phone):
        return json_fail("该手机号已被注册", 400)
    return success(None, "验证码已发送（测试码：123456）")


@router.post("/verify-code")
async def verify_code(form: VerifyCodeForm, db: AsyncSession = Depends(get_db)):
    """验证验证码：已注册手机号与错误验证码区分提示"""
    if await is_phone_registered(db, form.phone):
        return json_fail("该手机号已被注册", 400)
    if form.code != FAKE_CODE:
        return json_fail("验证码错误或已过期", 400)
    return success(None, "验证通过")


@router.post("/register")
async def register(form: RegisterForm, db: AsyncSession = Depends(get_db)):
    """注册：先验证码校验，再检查账号唯一性，最后创建用户"""
    if form.code != FAKE_CODE:
        return json_fail("请先完成手机验证", 400)

    if await check_user_exists(db, form.username, form.phone):
        return json_fail("账号或手机号已存在", 400)

    user = await create_user(db, form.username, form.password, form.phone, form.nickname)
    return success({"id": user.id, "username": user.username}, "注册成功")
