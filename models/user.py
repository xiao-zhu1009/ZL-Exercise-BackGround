# models/user.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    avatar: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # user/coach/admin
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1) # 0=禁用 1=启用
    goal: Mapped[str] = mapped_column(String(20), nullable=False, default="")
