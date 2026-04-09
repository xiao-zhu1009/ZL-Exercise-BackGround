# utils/jwt.py
# 职责：JWT Token 的签发与解析
# 依赖：core/config.py（取 SECRET_KEY、ALGORITHM、过期时间）
# 被依赖：
#   - api/auth.py 登录成功后调用 create_access_token 签发 Token
#   - utils/deps.py 校验请求时调用 decode_token 解析 Token

from datetime import datetime, timedelta
from jose import jwt
from core.config import settings

def create_access_token(data: dict) -> str:
    """签发 Token：将 payload 加上过期时间后用密钥签名"""
    payload = {
        **data,
        "exp": datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    """解析 Token：验证签名并返回 payload，过期或篡改会抛出 JWTError"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
