# models/diet.py
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, Date, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class Article(BaseModel):
    __tablename__ = "articles"

    author_id: Mapped[int] = mapped_column(Integer, nullable=False)                          # 发布教练的user_id
    title: Mapped[str] = mapped_column(String(200), nullable=False)                          # 文章标题
    category: Mapped[str] = mapped_column(String(30), nullable=False)                        # 分类：饮食/训练/新手/误区/身材管理/健康/工具/计划
    cover_img: Mapped[str] = mapped_column(String(500), nullable=False, default="")          # 封面图URL
    content: Mapped[str] = mapped_column(Text, nullable=True)                                # 文章正文
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")            # 文章摘要
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)              # 浏览次数
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)             # 审核状态：0=待审核 1=通过 2=驳回 3=下架
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")      # 驳回原因
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)                         # 审核人user_id
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)                   # 审核时间


class Food(BaseModel):
    __tablename__ = "foods"

    name: Mapped[str] = mapped_column(String(100), nullable=False)                            # 食物名称
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")               # 计量单位
    calories: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)      # 热量(kcal)，每100g/ml
    protein: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)       # 蛋白质(g)，每100g/ml
    carbs: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)         # 碳水化合物(g)，每100g/ml
    fat: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)           # 脂肪(g)，每100g/ml
    fiber: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)         # 膳食纤维(g)，每100g/ml
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="")            # 食物分类：主食/肉类/蔬菜/水果等
    is_custom: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)          # 来源：0=系统预置 1=教练投稿
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)             # 审核状态：0=待审核 1=通过 2=驳回；系统预置默认1
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")      # 驳回原因
    created_by: Mapped[int] = mapped_column(Integer, nullable=True)                          # 投稿教练的user_id，系统预置为空


class DietRecord(BaseModel):
    __tablename__ = "diet_records"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 记录所属用户
    food_id: Mapped[int] = mapped_column(Integer, nullable=True)                             # 关联foods.id，可为空（食物被删除后仍保留记录）
    food_name: Mapped[str] = mapped_column(String(100), nullable=False)                      # 食物名称（冗余存储，防止食物删除后丢失）
    meal_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)                     # 餐次：1=早餐 2=午餐 3=晚餐 4=加餐
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)                   # 摄入量
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")               # 计量单位
    calories: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)      # 本次摄入热量(kcal)，写入时计算
    protein: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)       # 本次摄入蛋白质(g)，写入时计算
    carbs: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)         # 本次摄入碳水(g)，写入时计算
    fat: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)           # 本次摄入脂肪(g)，写入时计算
    record_date: Mapped[date] = mapped_column(Date, nullable=False)                          # 饮食日期


class DietPlan(BaseModel):
    """教练为学员制定的饮食计划"""
    __tablename__ = "diet_plans"

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 制定计划的教练user_id
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)                         # 目标学员user_id
    title: Mapped[str] = mapped_column(String(200), nullable=False)                          # 计划标题
    goal: Mapped[str] = mapped_column(String(50), nullable=False)                            # 计划目标：减脂/增肌/均衡/增重
    start_date: Mapped[date] = mapped_column(Date, nullable=False)                           # 计划开始日期
    end_date: Mapped[date] = mapped_column(Date, nullable=False)                             # 计划结束日期
    description: Mapped[str] = mapped_column(Text, nullable=True)                            # 计划说明
    content: Mapped[dict] = mapped_column(JSON, nullable=True)                               # 每日餐次安排（JSON结构）
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)             # 计划状态：0=已终止 1=进行中 2=已完成
