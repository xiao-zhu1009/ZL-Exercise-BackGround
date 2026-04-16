# CRUD/body_stats.py
# 用户身体指标表的增删改查

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.body_stats import UserBodyStats

_BODY_FIELDS = ("height", "weight", "body_fat", "waist", "hip")


async def get_body_stats(db: AsyncSession, user_id: int):
    """查询用户身体指标"""
    result = await db.execute(select(UserBodyStats).where(UserBodyStats.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_body_stats_from_partial(db: AsyncSession, user_id: int, data: dict):
    """按 data 中出现的键新增或更新 user_body_stats，自动计算 BMI 和 WHR"""
    result = await db.execute(select(UserBodyStats).where(UserBodyStats.user_id == user_id))
    stats = result.scalar_one_or_none()

    if not stats:
        stats = UserBodyStats(user_id=user_id)
        db.add(stats)

    for field in _BODY_FIELDS:
        if field not in data:
            continue
        val = data[field]
        if val is not None:
            setattr(stats, field, val)

    if stats.height and stats.weight:
        stats.bmi = stats.weight / ((stats.height / 100) ** 2)

    if stats.waist and stats.hip:
        stats.whr = stats.waist / stats.hip

    await db.commit()
    return stats


async def upsert_body_stats(db: AsyncSession, user_id: int, form):
    """新增或更新身体指标，自动计算 BMI 和 WHR"""
    data = {f: getattr(form, f) for f in _BODY_FIELDS if getattr(form, f) is not None}
    return await upsert_body_stats_from_partial(db, user_id, data)
