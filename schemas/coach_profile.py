# schemas/coach_profile.py
# 教练主页接口的请求体定义

from pydantic import BaseModel
from typing import Optional


class CoachProfileUpdate(BaseModel):
    """教练主页修改：基本信息 + 教练专属字段，全部可选"""
    # 来自 users 表
    nickname:   Optional[str] = None
    phone:      Optional[str] = None
    signature:  Optional[str] = None
    goal:       Optional[str] = None
    # 来自 user_body_stats 表
    height:    Optional[float] = None
    weight:    Optional[float] = None
    body_fat:  Optional[float] = None
    waist:     Optional[float] = None
    hip:       Optional[float] = None
    # 来自 coach_profiles 表
    real_name:      Optional[str] = None
    gender:         Optional[int] = None   # 0=未设置 1=男 2=女
    age:            Optional[int] = None
    years_exp:      Optional[int] = None
    specialties:    Optional[str] = None   # 逗号分隔，如 "减脂,增肌,康复"
    certifications: Optional[str] = None
    intro:          Optional[str] = None
    location:       Optional[str] = None
    is_accepting:   Optional[int] = None   # 0=暂停招募 1=接受新学员
