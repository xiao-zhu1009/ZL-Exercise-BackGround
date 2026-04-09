# 【任务书】FastAPI + 异步 SQLAlchemy 基础配置

---

## 1. 需求说明

在 `ZL_fastapi_new` 项目中完成基础骨架搭建：
- 异步 SQLAlchemy 连接 MySQL 数据库
- 按职责拆分目录（db / models / schemas / api / core / utils）
- 统一响应格式 `{ code, msg, data }`
- JWT 鉴权中间件
- main.py 注册路由

---

## 2. 目录职责说明

```
ZL_fastapi_new/
├── main.py              # 应用入口，注册路由、中间件
├── db/
│   ├── __init__.py
│   └── session.py       # 异步引擎 + SessionLocal + get_db 依赖
├── models/
│   ├── __init__.py
│   └── user.py          # SQLAlchemy ORM 模型
├── schemas/
│   ├── __init__.py
│   └── user.py          # Pydantic 请求/响应模型
├── api/
│   ├── __init__.py
│   └── auth.py          # 登录/注册路由
├── core/
│   ├── __init__.py
│   └── config.py        # 环境变量配置（数据库URL、JWT密钥等）
└── utils/
    ├── __init__.py
    ├── jwt.py           # Token 签发与解析
    ├── deps.py          # get_current_user 依赖注入
    └── response.py      # 统一响应格式工具
```

---

## 3. 要做的事（按顺序）

### 第一步：安装依赖

```bash
pip install fastapi uvicorn sqlalchemy aiomysql python-jose[cryptography] passlib[bcrypt] python-dotenv
```

### 第二步：core/config.py — 环境变量

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str = "mysql+aiomysql://root:password@localhost:3306/zl_db"
    SECRET_KEY: str = "change-this-secret"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60 * 24

    class Config:
        env_file = ".env"

settings = Settings()
```

### 第三步：db/session.py — 异步数据库连接

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

engine = create_async_engine(settings.DB_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### 第四步：models/user.py — ORM 模型

```python
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.sql import func
from db.session import Base

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum("user", "coach", "admin"), default="user")
    nickname      = Column(String(50))
    created_at    = Column(DateTime, server_default=func.now())
```

### 第五步：schemas/user.py — Pydantic 模型

```python
from pydantic import BaseModel
from typing import Optional

class LoginForm(BaseModel):
    username: str
    password: str

class RegisterForm(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    nickname: Optional[str]

    class Config:
        from_attributes = True
```

### 第六步：utils/jwt.py — Token 工具

```python
from datetime import datetime, timedelta
from jose import jwt
from core.config import settings

def create_access_token(data: dict) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

### 第七步：utils/deps.py — 鉴权依赖注入

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from utils.jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
```

### 第八步：utils/response.py — 统一响应格式

```python
def success(data=None, msg="success"):
    return {"code": 200, "msg": msg, "data": data}

def fail(msg="error", code=400):
    return {"code": code, "msg": msg, "data": None}
```

### 第九步：api/auth.py — 登录注册路由

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from db.session import get_db
from models.user import User
from schemas.user import LoginForm, RegisterForm
from utils.jwt import create_access_token
from utils.response import success, fail

router = APIRouter(prefix="/auth", tags=["auth"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/login")
async def login(form: LoginForm, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not pwd.verify(form.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    token = create_access_token({"user_id": user.id, "role": user.role})
    return success({"id": user.id, "username": user.username, "role": user.role,
                    "nickname": user.nickname, "token": token}, "登录成功")

@router.post("/register")
async def register(form: RegisterForm, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=form.username, password_hash=pwd.hash(form.password),
                nickname=form.nickname)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return success({"id": user.id, "username": user.username}, "注册成功")
```

### 第十步：main.py — 注册路由 + 建表

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db.session import engine, Base
from api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
```

---

## 4. 接口设计

| 方法 | 路径 | 说明 | 需要 Token |
|------|------|------|-----------|
| POST | /auth/login | 登录 | 否 |
| POST | /auth/register | 注册 | 否 |

---

## 5. 数据库建表（手动建表时参考）

```sql
CREATE TABLE users (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('user','coach','admin') NOT NULL DEFAULT 'user',
  nickname      VARCHAR(50),
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. 运行

```bash
# 创建 .env 文件
DB_URL=mysql+aiomysql://root:你的密码@localhost:3306/zl_db
SECRET_KEY=你的随机密钥

# 启动
uvicorn main:app --reload --port 8000
```
