# utils/deps.py
# 职责：FastAPI 依赖注入 —— 从请求头提取并校验 Token，返回当前用户信息
# 依赖：utils/jwt.py（解析 Token）
# 被依赖：需要登录才能访问的路由，在参数里写 current_user = Depends(get_current_user)
#
# 请求流向：
#   HTTP 请求 → FastAPI 读取 Authorization: Bearer <token>
#   → oauth2_scheme 提取 token 字符串
#   → get_current_user 调用 decode_token 校验
#   → 校验通过：把 payload（含 user_id、role）注入路由函数
#   → 校验失败：直接返回 401，路由函数不会执行

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from utils.jwt import decode_token

# tokenUrl 仅用于 Swagger 文档的"Authorize"按钮，指向登录接口
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)   # 返回 {"user_id": 1, "role": "user", "exp": ...}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
