# CRUD/coach_application.py
# 教练申请的数据库操作

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.coach_application import CoachApplication


async def get_pending_by_user(db: AsyncSession, user_id: int):
    """查用户是否有待审申请"""
    result = await db.execute(
        select(CoachApplication).where(
            CoachApplication.user_id == user_id,
            CoachApplication.status == "pending",
            CoachApplication.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def get_latest_by_user(db: AsyncSession, user_id: int):
    """查用户最新一条申请（按 id 倒序）"""
    result = await db.execute(
        select(CoachApplication).where(
            CoachApplication.user_id == user_id,
            CoachApplication.is_deleted == 0,
        ).order_by(CoachApplication.id.desc())
    )
    return result.scalars().first()


async def create_application(db: AsyncSession, user_id: int, reason: str):
    """新建申请记录"""
    app = CoachApplication(user_id=user_id, reason=reason)
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def get_application_by_id(db: AsyncSession, app_id: int):
    """按 ID 查申请"""
    result = await db.execute(
        select(CoachApplication).where(
            CoachApplication.id == app_id,
            CoachApplication.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def get_applications(db: AsyncSession, status: str = None):
    """管理端：查申请列表，可按状态过滤"""
    q = select(CoachApplication).where(CoachApplication.is_deleted == 0)
    if status:
        q = q.where(CoachApplication.status == status)
    q = q.order_by(CoachApplication.id.desc())
    result = await db.execute(q)
    return result.scalars().all()


async def approve_application(db: AsyncSession, app: CoachApplication, reviewed_by: int):
    """通过申请"""
    app.status = "approved"
    app.reviewed_by = reviewed_by
    await db.commit()


async def reject_application(db: AsyncSession, app: CoachApplication, reviewed_by: int, reject_reason: str):
    """拒绝申请"""
    app.status = "rejected"
    app.reviewed_by = reviewed_by
    app.reject_reason = reject_reason
    await db.commit()
