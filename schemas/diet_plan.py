# schemas/diet_plan.py
from datetime import date
from typing import Optional
from pydantic import BaseModel


class DietPlanCreate(BaseModel):
    title: str
    goal: str                          # 减脂/增肌/均衡/增重
    start_date: date
    end_date: date
    description: Optional[str] = ""
    content: Optional[dict] = None     # 每日餐次安排 JSON
    student_id: int                    # 教练端必传


# 学员自拟计划，无需 student_id
class SelfDietPlanCreate(BaseModel):
    title: str
    goal: str
    start_date: date
    end_date: date
    description: Optional[str] = ""
    content: Optional[dict] = None


class DietPlanStatusUpdate(BaseModel):
    status: int                        # 0=终止 2=完成
