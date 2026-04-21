# api/auth.py
# 认证路由：登录、注册、验证码

import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.user import LoginForm, RegisterForm, SendCodeForm, VerifyCodeForm, ForgotPasswordSendCode, ResetPasswordForm
from utils.jwt import create_access_token
from utils.response import success, json_fail
from CRUD.user import (
    get_user_by_account,
    get_user_by_phone,
    check_user_exists,
    create_user,
    save_user_token,
    is_phone_registered,
    update_user_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# 测试用验证码，后续替换为真实短信服务
FAKE_CODE = "123456"

# 忘记密码验证码存储：{phone: (code, expire_timestamp)}
_reset_code_store: dict[str, tuple[str, float]] = {}
RESET_CODE_TTL = 300  # 5 分钟有效期

# 登录接口
@router.post("/login")
async def login(form: LoginForm, db: AsyncSession = Depends(get_db)):
    """登录：支持账号或手机号"""
    user = await get_user_by_account(db, form.account)
    if not user:
        return json_fail("账号未注册", 401)
    if user.password != form.password:
        return json_fail("密码错误", 401)
    if user.status == 0:
        return json_fail("账号已被封禁，请联系管理员", 403)

    token = create_access_token({"user_id": user.id, "role": user.role})
    await save_user_token(db, user, token)

    return success({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "nickname": user.nickname,
        "avatar": user.avatar or "",
        "token": token
    }, "登录成功")

# 模拟发送验证码接口
@router.post("/send-code")
async def send_code(form: SendCodeForm, db: AsyncSession = Depends(get_db)):
    """发送验证码（当前为测试模式，固定返回 123456）"""
    if await is_phone_registered(db, form.phone):
        return json_fail("该手机号已被注册", 400)
    return success(None, "验证码已发送（测试码：123456）")

# 前端填写验证码验证接口
@router.post("/verify-code")
async def verify_code(form: VerifyCodeForm, db: AsyncSession = Depends(get_db)):
    """验证验证码：已注册手机号与错误验证码区分提示"""
    if await is_phone_registered(db, form.phone):
        return json_fail("该手机号已被注册", 400)
    if form.code != FAKE_CODE:
        return json_fail("验证码错误或已过期", 400)
    return success(None, "验证通过")

# 账号信息注册接口
@router.post("/register")
async def register(form: RegisterForm, db: AsyncSession = Depends(get_db)):
    """注册：先验证码校验，再检查账号唯一性，最后创建用户"""
    if form.code != FAKE_CODE:
        return json_fail("请先完成手机验证", 400)

    if await check_user_exists(db, form.username, form.phone):
        return json_fail("账号或手机号已存在", 400)

    user = await create_user(db, form.username, form.password, form.phone, form.nickname)
    return success({"id": user.id, "username": user.username}, "注册成功")


# 忘记密码 - 发送验证码
@router.post("/forgot-password/send-code")
async def forgot_password_send_code(form: ForgotPasswordSendCode, db: AsyncSession = Depends(get_db)):
    """忘记密码：向已注册手机号发送验证码"""
    user = await get_user_by_phone(db, form.phone)
    if not user:
        return json_fail("该手机号未注册", 400)

    # 存储验证码（测试模式固定 123456）
    _reset_code_store[form.phone] = (FAKE_CODE, time.time() + RESET_CODE_TTL)
    return success(None, "验证码已发送（测试码：123456）")


# 忘记密码 - 验证码校验并重置密码
@router.post("/forgot-password/reset")
async def forgot_password_reset(form: ResetPasswordForm, db: AsyncSession = Depends(get_db)):
    """忘记密码：验证码通过后重置密码"""
    entry = _reset_code_store.get(form.phone)
    if not entry:
        return json_fail("请先获取验证码", 400)

    code, expire_at = entry
    if time.time() > expire_at:
        _reset_code_store.pop(form.phone, None)
        return json_fail("验证码已过期，请重新获取", 400)
    if form.code != code:
        return json_fail("验证码错误", 400)

    user = await get_user_by_phone(db, form.phone)
    if not user:
        return json_fail("用户不存在", 400)

    await update_user_password(db, user, form.new_password)
    _reset_code_store.pop(form.phone, None)  # 用完即删
    return success(None, "密码重置成功")
