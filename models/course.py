# models/course.py
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)          # 有氧/力量/瑜伽
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 1=初级 2=中级 3=高级
    description: Mapped[str] = mapped_column(Text, nullable=True)
    cover_img: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    max_people: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    enrolled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 0=下架 1=招募中 2=满员 3=已结束


class Reservation(BaseModel):
    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uk_user_course"),
    )

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 0=已取消 1=已预约 2=已完成
    cancel_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
