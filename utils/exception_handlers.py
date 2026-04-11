# utils/exception_handlers.py
# 参数校验错误 → 统一 { code, message, data }
# HTTPException：供依赖注入（如 get_current_user）、OAuth2 等仍 raise 的场景统一格式；业务路由请用 return json_fail()

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from utils.response import fail


def _http_detail_message(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, (list, tuple)):
        parts = []
        for item in detail:
            if isinstance(item, dict) and "msg" in item:
                parts.append(str(item["msg"]))
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "请求错误"
    if isinstance(detail, dict):
        if "msg" in detail:
            return str(detail["msg"])
        return str(detail)
    return str(detail)


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    message = _http_detail_message(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(message, exc.status_code),
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = "参数校验失败"
    if errors:
        message = str(errors[0].get("msg", message))
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": message, "data": errors},
    )
