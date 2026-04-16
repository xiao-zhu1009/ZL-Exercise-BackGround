# utils/public_url.py
# 生成浏览器可访问的静态资源绝对 URL（头像等）

from fastapi import Request

from config.settings import settings


def public_origin(request: Request) -> str:
    """
    站点根 URL（无末尾 /），用于拼接 /api/static/...
    优先 settings.PUBLIC_BASE_URL（局域网、反代、Docker 时与 request.base_url 不一致时必配）。
    """
    override = getattr(settings, "PUBLIC_BASE_URL", None)
    if override and str(override).strip():
        return str(override).strip().rstrip("/")
    return str(request.base_url).rstrip("/")


def static_file_public_url(request: Request, *path_parts: str) -> str:
    """path_parts 例如 ('avatars', '1_abc.jpg') → {origin}/api/static/avatars/1_abc.jpg"""
    sub = "/".join(path_parts)
    return f"{public_origin(request)}/api/static/{sub}"
