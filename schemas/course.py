# schemas/course.py
# 课程与预约请求数据校验模型
# CourseCreate：教练发布新课程
# CourseUpdate：教练修改被驳回的课程（字段全部可选）
# CourseReview：管理员审核（通过/驳回）
# ReservationAction：教练审批预约（确认/拒绝）

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class CourseCreate(BaseModel):
    title: str
    category: str                          # 有氧/力量/瑜伽/综合
    difficulty: int = 1                    # 1初级 2中级 3高级
    description: Optional[str] = ""
    cover_img: str = ""
    price: float = 0
    max_people: int = 10
    start_time: str                        # 格式 YYYY-MM-DD HH:MM:SS
    end_time: Optional[str] = None
    location: str = ""


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[int] = None
    description: Optional[str] = None
    cover_img: Optional[str] = None
    price: Optional[float] = None
    max_people: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None


class CourseReview(BaseModel):
    status: int                            # 1=通过  4=驳回
    reject_reason: Optional[str] = ""     # 驳回时必填


class ReservationAction(BaseModel):
    status: int                            # 2=确认  3=拒绝
    cancel_reason: Optional[str] = ""     # 拒绝时可填原因
