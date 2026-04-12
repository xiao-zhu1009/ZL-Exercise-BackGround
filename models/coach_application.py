# models/coach_application.py
# 教练申请记录表：记录用户申请成为教练的流程状态

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.session import BaseModel


class CoachApplication(BaseModel):
    __tablename__ = "coach_applications"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    # pending=待审 approved=通过 rejected=拒绝
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")       # 申请说明
    reject_reason: Mapped[str] = mapped_column(String(500), nullable=False, default="") # 拒绝原因
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=True)                   # 审核人 user_id
