# CRUD/diet_plan.py
# 饮食计划数据层：教练创建/查询/更新，学员查询

from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.diet import DietPlan
from models.training import CoachStudent


async def create_diet_plan(db: AsyncSession, coach_id: int, student_id: int, data: dict) -> DietPlan:
    """教练为学员创建饮食计划"""
    plan = DietPlan(coach_id=coach_id, student_id=student_id, **data)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_diet_plans_for_student(db: AsyncSession, student_id: int, status: int = None):
    """学员查询自己的饮食计划列表"""
    stmt = select(DietPlan).where(
        DietPlan.student_id == student_id,
        DietPlan.is_deleted == 0,
    )
    if status is not None:
        stmt = stmt.where(DietPlan.status == status)
    stmt = stmt.order_by(DietPlan.start_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_diet_plan_by_id(db: AsyncSession, plan_id: int) -> DietPlan | None:
    """按 ID 查单条饮食计划"""
    result = await db.execute(
        select(DietPlan).where(DietPlan.id == plan_id, DietPlan.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def get_diet_plans_by_coach_student(db: AsyncSession, coach_id: int, student_id: int):
    """教练查询为某学员制定的饮食计划列表"""
    result = await db.execute(
        select(DietPlan).where(
            DietPlan.coach_id == coach_id,
            DietPlan.student_id == student_id,
            DietPlan.is_deleted == 0,
        ).order_by(DietPlan.start_date.desc())
    )
    return result.scalars().all()


async def update_diet_plan_status(db: AsyncSession, plan: DietPlan, status: int) -> DietPlan:
    """更新饮食计划状态（0=终止 2=完成）"""
    plan.status = status
    await db.commit()
    return plan
