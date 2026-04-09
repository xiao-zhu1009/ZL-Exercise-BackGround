# models/user.py
# 职责：定义 users 表的 ORM 映射，描述数据库表结构
# 依赖：db/session.py（导入 Base）
# 被依赖：api/auth.py（查询/插入用户记录）

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, default="健身用户_xxxx")
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, default="https://cube.elemecdn.com/9/c2/f0e28622d4d897f566126cfc54704jpeg.jpeg")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")