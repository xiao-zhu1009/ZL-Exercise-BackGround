# utils/deps.py
# 鉴权依赖：解析 Token，验证用户是否登录

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.jwt import decode_token
from db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """解析 Token，返回 payload（含 user_id、role）"""
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    from models.user import User
    result = await db.execute(select(User).where(User.id == payload["user_id"], User.token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Token 已失效，请重新登录")

    # 以数据库中的 role 为准，审批通过后无需重新登录即可生效
    payload["role"] = user.role
    return payload
