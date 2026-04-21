# models/user.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)   # 登录账号，全局唯一
    password: Mapped[str] = mapped_column(String(255), nullable=False)               # 登录密码
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, default="")    # 昵称
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="")       # 手机号
    avatar: Mapped[str] = mapped_column(String(1024), nullable=False, default="")    # 头像完整URL
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")    # 角色：user/coach/admin
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)          # 账号状态：0=禁用 1=启用
    goal: Mapped[str] = mapped_column(String(20), nullable=False, default="")        # 健身目标
    signature: Mapped[str] = mapped_column(String(100), nullable=False, default="")  # 个人签名
    token: Mapped[str] = mapped_column(String(500), nullable=False, default="")      # 当前有效JWT，封禁或角色变更时清空
