# schemas/user.py
# 职责：定义接口的请求体和响应体结构，FastAPI 用它做自动校验和文档生成
# 依赖：无（纯 Pydantic，不依赖项目内其他模块）
# 被依赖：api/auth.py（路由函数的参数类型和返回类型）
# 注意：schemas 描述"接口数据形状"，models 描述"数据库表结构"，两者分开维护

from pydantic import BaseModel
from typing import Optional

# ── 请求体 ──────────────────────────────────────────────

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

# ── 响应体 ──────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    nickname: Optional[str]

    class Config:
        from_attributes = True  # 允许从 ORM 对象直接转换（SQLAlchemy model → Pydantic）
