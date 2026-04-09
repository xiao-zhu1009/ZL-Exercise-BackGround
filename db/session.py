# db/session.py
# 职责：创建异步数据库引擎，提供 Session 工厂和 get_db 依赖函数
# 依赖：core/config.py（取数据库连接串）
# 被依赖：
#   - models/*.py 导入 Base 来定义 ORM 模型
#   - main.py 导入 engine + Base 在启动时建表
#   - api/*.py 通过 Depends(get_db) 获取数据库会话

from datetime import datetime
from sqlalchemy import Integer, SmallInteger, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Mapped, mapped_column
from core.config import settings

# 异步引擎：echo=True 会在控制台打印 SQL，调试时方便，生产可改为 False
engine = create_async_engine(settings.DB_URL, echo=True)

# Session 工厂：每次请求通过 get_db() 创建一个独立的 AsyncSession
# expire_on_commit=False：提交后对象属性不失效，避免异步场景下的懒加载问题
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 所有 ORM 模型的基类，models/*.py 里的 class User(Base) 都继承它
Base = declarative_base()

# 公共字段抽象基类：所有业务表继承此类，自动获得 id/created_at/updated_at/is_deleted
class BaseModel(Base):
    __abstract__ = True  # 声明为抽象类，不会生成数据库表

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

# FastAPI 依赖函数：用 yield 保证请求结束后自动关闭 session
# 用法：在路由函数参数里写 db: AsyncSession = Depends(get_db)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
