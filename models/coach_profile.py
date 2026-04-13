# models/coach_profile.py
# 教练扩展信息表：存储教练专属字段，与 users 表 1:1 关联

from sqlalchemy import Integer, String, Text, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class CoachProfile(BaseModel):
    __tablename__ = "coach_profiles"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    gender: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)   # 0=未设置 1=男 2=女
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    years_exp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)     # 从业年限
    specialties: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 逗号分隔，如"减脂,增肌"
    certifications: Mapped[str] = mapped_column(Text, nullable=True)               # 资质证书描述
    intro: Mapped[str] = mapped_column(Text, nullable=True)                        # 详细介绍
    location: Mapped[str] = mapped_column(String(100), nullable=False, default="") # 所在城市
    is_accepting: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 0=暂停招募 1=接受新学员
