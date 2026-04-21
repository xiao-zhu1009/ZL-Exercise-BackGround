# models/course.py
# 课程表与预约表 ORM 模型
# Course：教练发布的课程，含审核流程字段
# Reservation：用户预约记录，含教练审批状态

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    coach_id: Mapped[int] = mapped_column(Integer, nullable=False)                          # 发布教练的user_id
    title: Mapped[str] = mapped_column(String(200), nullable=False)                         # 课程标题
    category: Mapped[str] = mapped_column(String(30), nullable=False)                       # 课程类别：有氧/力量/瑜伽/综合
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)        # 难度：1=初级 2=中级 3=高级
    description: Mapped[str] = mapped_column(Text, nullable=True)                           # 课程详情描述
    cover_img: Mapped[str] = mapped_column(String(500), nullable=False, default="")         # 封面图URL
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)       # 课程价格（元）
    max_people: Mapped[int] = mapped_column(Integer, nullable=False, default=10)            # 最大报名人数
    enrolled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)               # 已确认报名人数，教练审批通过后+1
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)                  # 开课时间
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)                     # 结课时间
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")          # 上课地点
    # 课程状态：0=待审核 1=招募中 2=满员 3=已结束 4=已驳回 5=已下架
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")     # 驳回原因
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)                        # 审核人user_id
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)                  # 审核时间


class Reservation(BaseModel):
    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uk_user_course"),
    )

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)                            # 预约用户的user_id
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)                          # 关联courses.id
    # 预约状态：0=已取消 1=待审批 2=已确认 3=已拒绝
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    cancel_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")      # 取消原因
