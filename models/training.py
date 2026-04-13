# models/training.py
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, Date, Numeric, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class BodyRecord(BaseModel):
    __tablename__ = "body_records"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    height: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    bmi: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    remark: Mapped[str] = mapped_column(String(255), nullable=False, default="")


class WorkoutRecord(BaseModel):
    __tablename__ = "workout_records"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 训练时长（分钟）
    calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 消耗卡路里
    workout_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    extra: Mapped[dict] = mapped_column(JSON, nullable=True)


class TrainingPlan(BaseModel):
    __tablename__ = "training_plans"

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)              # 减脂/增肌/塑形/提升耐力
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 0=已终止 1=进行中 2=已完成


class CoachStudent(BaseModel):
    __tablename__ = "coach_students"
    __table_args__ = (
        UniqueConstraint("coach_id", "student_id", name="uk_coach_student"),
    )

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # pending=待教练同意 active=已绑定 rejected=已拒绝 ended=已解绑
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    request_msg: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 申请留言
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 拒绝原因
    bind_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
