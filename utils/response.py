# utils/response.py
# 职责：统一接口响应格式 { code, msg, data }，与前端约定保持一致
# 依赖：无
# 被依赖：api/*.py 所有路由函数用 success() / fail() 包装返回值

def success(data=None, msg="success"):
    return {"code": 200, "msg": msg, "data": data}

def fail(msg="error", code=400):
    return {"code": code, "msg": msg, "data": None}
