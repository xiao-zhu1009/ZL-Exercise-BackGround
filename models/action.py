# models/action.py
from datetime import datetime
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel

class Action(BaseModel):
    __tablename__ = "actions"

    author_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body_part: Mapped[str] = mapped_column(String(20), nullable=False)         # 胸/腿/背/肩/核心
    category: Mapped[str] = mapped_column(String(20), nullable=False)          # 力量/有氧/拉伸/综合
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)  # 1=初级 2=中级 3=高级
    cover_img: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    video_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    steps: Mapped[dict] = mapped_column(JSON, nullable=True)
    cautions: Mapped[dict] = mapped_column(JSON, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)  # 0=待审核 1=通过 2=拒绝
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
