# models/training.py
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, Date, Numeric, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class BodyRecord(BaseModel):
    __tablename__ = "body_records"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 记录所属用户
    record_date: Mapped[date] = mapped_column(Date, nullable=False)                          # 体测日期
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)                   # 体重 kg
    body_fat: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)                 # 体脂率 %
    waist: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)                    # 腰围 cm
    chest: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)                    # 胸围 cm
    remark: Mapped[str] = mapped_column(String(255), nullable=False, default="")             # 备注


class WorkoutRecord(BaseModel):
    __tablename__ = "workout_records"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 记录所属用户
    record_date: Mapped[date] = mapped_column(Date, nullable=False)                          # 训练日期
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)               # 训练时长（分钟）
    calories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)               # 消耗热量（kcal）
    workout_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")       # 训练类型
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")              # 训练备注
    extra: Mapped[dict] = mapped_column(JSON, nullable=True)                                 # 扩展数据（如动作组数、重量等JSON结构）


class TrainingPlan(BaseModel):
    __tablename__ = "training_plans"

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 制定计划的教练user_id
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)                         # 目标学员user_id
    title: Mapped[str] = mapped_column(String(200), nullable=False)                          # 计划标题
    goal: Mapped[str] = mapped_column(String(50), nullable=False)                            # 计划目标：减脂/增肌/塑形/提升耐力
    start_date: Mapped[date] = mapped_column(Date, nullable=False)                           # 计划开始日期
    end_date: Mapped[date] = mapped_column(Date, nullable=False)                             # 计划结束日期
    description: Mapped[str] = mapped_column(Text, nullable=True)                            # 计划说明
    content: Mapped[dict] = mapped_column(JSON, nullable=True)                               # 每日训练安排（JSON结构）
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)             # 计划状态：0=已终止 1=进行中 2=已完成


class CoachStudent(BaseModel):
    __tablename__ = "coach_students"
    __table_args__ = (
        UniqueConstraint("coach_id", "student_id", name="uk_coach_student"),
    )

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 教练user_id
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)                         # 学员user_id
    # 绑定状态：pending=待教练同意 active=已绑定 rejected=已拒绝 ended=已解绑
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    request_msg: Mapped[str] = mapped_column(String(255), nullable=False, default="")        # 学员申请留言
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")      # 教练拒绝原因
    bind_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)                       # 绑定生效时间
