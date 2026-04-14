# schemas/training.py
# 训练模块请求/响应 Schema：身体记录、训练记录新增、训练计划新增

from datetime import date
from typing import Optional
from pydantic import BaseModel


class BodyRecordCreate(BaseModel):
    """新增/修改身体记录请求体"""
    record_date: date
    weight: Optional[float] = None      # 体重 kg
    body_fat: Optional[float] = None    # 体脂率 %
    waist: Optional[float] = None       # 腰围 cm
    chest: Optional[float] = None       # 胸围 cm
    remark: Optional[str] = ""


class WorkoutRecordCreate(BaseModel):
    """新增训练记录请求体"""
    record_date: date
    duration: int           # 训练时长（分钟），必须 > 0
    calories: int           # 消耗卡路里，必须 >= 0
    workout_type: str       # 训练类型：力量/有氧/瑜伽/球类/其他
    note: Optional[str] = ""
    # 详细模式动作列表，结构：{ mode: "detail", exercises: [{name, sets, reps, weight, unit, note}] }
    extra: Optional[dict] = None


class TrainingPlanCreate(BaseModel):
    """新增训练计划请求体（用户自建或教练为学员创建）"""
    title: str
    goal: str               # 减脂/增肌/塑形/提升耐力
    start_date: date
    end_date: date
    description: Optional[str] = ""
    content: Optional[dict] = None
    student_id: Optional[int] = None   # 教练端传入；用户端不传（后端用 current_user）
