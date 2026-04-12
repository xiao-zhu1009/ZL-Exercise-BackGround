# schemas/coach_application.py
# 教练申请相关的请求体和响应体

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApplyForm(BaseModel):
    reason: str  # 申请说明


class RejectForm(BaseModel):
    reject_reason: str  # 拒绝原因


class ApplicationOut(BaseModel):
    id: int
    user_id: int
    status: str
    reason: str
    reject_reason: str
    reviewed_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationAdminOut(ApplicationOut):
    """管理端额外返回申请人信息"""
    username: Optional[str] = None
    nickname: Optional[str] = None
