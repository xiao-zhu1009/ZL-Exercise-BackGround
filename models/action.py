# models/action.py
from datetime import datetime
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel

class Action(BaseModel):
    __tablename__ = "actions"

    author_id: Mapped[int] = mapped_column(Integer, nullable=False)                          # 发布教练的user_id
    title: Mapped[str] = mapped_column(String(100), nullable=False)                          # 动作名称
    body_part: Mapped[str] = mapped_column(String(20), nullable=False)                       # 训练部位：胸/腿/背/肩/核心
    category: Mapped[str] = mapped_column(String(20), nullable=False)                        # 动作类别：力量/有氧/拉伸/综合
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)         # 难度：1=初级 2=中级 3=高级
    cover_img: Mapped[str] = mapped_column(String(500), nullable=False, default="")          # 封面图URL
    video_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")          # 演示视频URL
    description: Mapped[str] = mapped_column(Text, nullable=True)                            # 动作描述
    steps: Mapped[dict] = mapped_column(JSON, nullable=True)                                 # 动作步骤列表（JSON数组）
    cautions: Mapped[dict] = mapped_column(JSON, nullable=True)                              # 注意事项列表（JSON数组）
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)              # 浏览次数
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)             # 审核状态：0=待审核 1=通过 2=驳回 3=下架
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")      # 驳回原因
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)                         # 审核人user_id
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)                   # 审核时间
