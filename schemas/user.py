# schemas/user.py
# 接口请求体和响应体的数据结构定义，FastAPI 用它做自动校验

from pydantic import BaseModel
from typing import Optional


# ── 认证相关 ──────────────────────────────────────────────

class LoginForm(BaseModel):
    account: str   # 账号或手机号
    password: str

class SendCodeForm(BaseModel):
    phone: str

class VerifyCodeForm(BaseModel):
    phone: str
    code: str

class RegisterForm(BaseModel):
    phone: str
    code: str
    username: str
    password: str
    nickname: Optional[str] = None


# ── 用户信息相关 ──────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    nickname: Optional[str]

    class Config:
        from_attributes = True  # 允许从 ORM 对象直接转换

class ProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    phone: Optional[str] = None
    signature: Optional[str] = None
    avatar: Optional[str] = None  # 传空字符串 "" 表示恢复默认头像

class BodyStatsUpdate(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordSendCode(BaseModel):
    phone: str

class ResetPasswordForm(BaseModel):
    phone: str
    code: str
    new_password: str
