# utils/jwt.py
# Token 签发与解析

from datetime import datetime, timedelta
from uuid import uuid4
from jose import jwt
from config.settings import settings

def create_access_token(data: dict) -> str:
    """签发 Token"""
    payload = {
        **data,
        "exp": datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
        "jti": uuid4().hex  # 唯一标识，防止同秒登录生成相同 token
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    """解析 Token，签名错误或过期会抛出 JWTError"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
