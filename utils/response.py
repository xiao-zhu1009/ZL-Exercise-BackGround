# utils/response.py
# 统一接口响应格式，所有路由用 success() / json_fail() 返回

from fastapi.responses import JSONResponse


def success(data=None, message="success"):
    return {"code": 200, "message": message, "data": data}


def fail(message="error", code=400):
    return {"code": code, "message": message, "data": None}


def json_fail(message="error", code=400):
    """业务错误：HTTP 状态码与 body.code 一致，便于前端按统一信封解析。"""
    return JSONResponse(status_code=code, content=fail(message, code))
