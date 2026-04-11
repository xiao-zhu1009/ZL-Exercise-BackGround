# CRUD/body_stats.py
# 用户身体指标表的增删改查

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.body_stats import UserBodyStats


async def get_body_stats(db: AsyncSession, user_id: int):
    """查询用户身体指标"""
    result = await db.execute(select(UserBodyStats).where(UserBodyStats.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_body_stats(db: AsyncSession, user_id: int, form):
    """新增或更新身体指标，自动计算 BMI 和 WHR"""
    result = await db.execute(select(UserBodyStats).where(UserBodyStats.user_id == user_id))
    stats = result.scalar_one_or_none()

    if not stats:
        stats = UserBodyStats(user_id=user_id)
        db.add(stats)

    # 只更新传入的字段
    for field in ("height", "weight", "body_fat", "waist", "hip"):
        val = getattr(form, field)
        if val is not None:
            setattr(stats, field, val)

    # 自动计算 BMI（体重 / 身高²）
    if stats.height and stats.weight:
        stats.bmi = stats.weight / ((stats.height / 100) ** 2)

    # 自动计算 WHR（腰围 / 臀围）
    if stats.waist and stats.hip:
        stats.whr = stats.waist / stats.hip

    await db.commit()
    return stats
