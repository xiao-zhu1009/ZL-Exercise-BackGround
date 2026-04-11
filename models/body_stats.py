# models/body_stats.py
from sqlalchemy import Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel

class UserBodyStats(BaseModel):
    __tablename__ = "user_body_stats"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    height: Mapped[float] = mapped_column(Float, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=True)
    bmi: Mapped[float] = mapped_column(Float, nullable=True)
    body_fat: Mapped[float] = mapped_column(Float, nullable=True)
    waist: Mapped[float] = mapped_column(Float, nullable=True)
    hip: Mapped[float] = mapped_column(Float, nullable=True)
    whr: Mapped[float] = mapped_column(Float, nullable=True)
