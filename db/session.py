# db/session.py
# 数据库引擎、Session 工厂、公共基类，以及 get_db 依赖函数

from datetime import datetime
from sqlalchemy import Integer, SmallInteger, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Mapped, mapped_column
from config.settings import settings

# echo=True 会在控制台打印 SQL，生产环境可改为 False
engine = create_async_engine(settings.DB_URL, echo=True)

# expire_on_commit=False：提交后对象属性不失效，避免异步懒加载报错
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 所有 ORM 模型的基类
Base = declarative_base()

# 公共字段基类：业务表继承后自动拥有 id / created_at / updated_at / is_deleted
class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

# FastAPI 依赖：用 yield 保证请求结束后自动关闭 session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
