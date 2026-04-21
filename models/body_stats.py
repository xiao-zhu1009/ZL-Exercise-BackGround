# models/body_stats.py
from sqlalchemy import Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel

class UserBodyStats(BaseModel):
    __tablename__ = "user_body_stats"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)  # 关联users.id，一对一
    height: Mapped[float] = mapped_column(Float, nullable=True)                # 身高 cm
    weight: Mapped[float] = mapped_column(Float, nullable=True)                # 体重 kg
    bmi: Mapped[float] = mapped_column(Float, nullable=True)                   # BMI 体质指数
    body_fat: Mapped[float] = mapped_column(Float, nullable=True)              # 体脂率 %
    waist: Mapped[float] = mapped_column(Float, nullable=True)                 # 腰围 cm
    hip: Mapped[float] = mapped_column(Float, nullable=True)                   # 臀围 cm
    whr: Mapped[float] = mapped_column(Float, nullable=True)                   # 腰臀比
