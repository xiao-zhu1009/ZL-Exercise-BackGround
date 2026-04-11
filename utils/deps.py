# utils/deps.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.jwt import decode_token
from db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    from models.user import User
    result = await db.execute(select(User).where(User.id == payload["user_id"], User.token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Token 已失效，请重新登录")

    return payload
