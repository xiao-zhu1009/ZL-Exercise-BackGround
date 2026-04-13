# models/diet.py
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, Date, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class DietArticle(BaseModel):
    __tablename__ = "diet_articles"

    author_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)          # 增肌餐/减脂餐/均衡饮食/补剂知识
    cover_img: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)  # 0=待审核 1=通过 2=拒绝
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Food(BaseModel):
    __tablename__ = "foods"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    calories: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    protein: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    carbs: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    fat: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    fiber: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="")  # 主食/肉类/蔬菜/水果等
    is_custom: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)  # 0=系统库 1=教练投稿
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)     # 0=待审核 1=通过 2=驳回；系统预置默认1
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_by: Mapped[int] = mapped_column(Integer, nullable=True)


class DietRecord(BaseModel):
    __tablename__ = "diet_records"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    food_id: Mapped[int] = mapped_column(Integer, nullable=True)
    food_name: Mapped[str] = mapped_column(String(100), nullable=False)        # 冗余存储，防止食物删除后丢失
    meal_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)       # 1=早餐 2=午餐 3=晚餐 4=加餐
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    calories: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    protein: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    carbs: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    fat: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)


class DietPlan(BaseModel):
    """教练为学员制定的饮食计划"""
    __tablename__ = "diet_plans"

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)              # 减脂/增肌/均衡/增重
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=True)                 # 每日餐次安排
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 0=已终止 1=进行中 2=已完成
