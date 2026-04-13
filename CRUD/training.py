# CRUD/training.py
# 训练模块数据层：训练记录增删查、训练计划增查、教练学员查询、统计图表数据

from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.training import WorkoutRecord, TrainingPlan, CoachStudent
from models.user import User


async def get_workout_records(db: AsyncSession, user_id: int, start: date, end: date):
    """查询用户指定日期区间内的训练记录，按日期倒序"""
    result = await db.execute(
        select(WorkoutRecord)
        .where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.record_date >= start,
            WorkoutRecord.record_date <= end,
            WorkoutRecord.is_deleted == 0,
        )
        .order_by(WorkoutRecord.record_date.desc())
    )
    return result.scalars().all()


async def create_workout_record(db: AsyncSession, user_id: int, data: dict):
    """新增一条训练记录"""
    record = WorkoutRecord(user_id=user_id, **data)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_workout_record(db: AsyncSession, record_id: int, user_id: int) -> bool:
    """软删除训练记录，仅本人可操作"""
    result = await db.execute(
        select(WorkoutRecord).where(
            WorkoutRecord.id == record_id,
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    record.is_deleted = 1
    await db.commit()
    return True


async def get_training_plans(db: AsyncSession, user_id: int, status: int = None):
    """查询用户的训练计划，status=None 时返回全部"""
    stmt = select(TrainingPlan).where(
        TrainingPlan.student_id == user_id,
        TrainingPlan.is_deleted == 0,
    )
    if status is not None:
        stmt = stmt.where(TrainingPlan.status == status)
    stmt = stmt.order_by(TrainingPlan.start_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_daily_stats(db: AsyncSession, user_id: int, start: date, end: date):
    """按天汇总训练时长和卡路里，用于折线/柱状图"""
    result = await db.execute(
        select(
            WorkoutRecord.record_date,
            func.sum(WorkoutRecord.duration).label("duration"),
            func.sum(WorkoutRecord.calories).label("calories"),
        )
        .where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.record_date >= start,
            WorkoutRecord.record_date <= end,
            WorkoutRecord.is_deleted == 0,
        )
        .group_by(WorkoutRecord.record_date)
        .order_by(WorkoutRecord.record_date)
    )
    return result.all()


async def get_type_stats(db: AsyncSession, user_id: int, start: date, end: date):
    """按训练类型汇总次数，用于饼图"""
    result = await db.execute(
        select(
            WorkoutRecord.workout_type,
            func.count(WorkoutRecord.id).label("count"),
        )
        .where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.record_date >= start,
            WorkoutRecord.record_date <= end,
            WorkoutRecord.is_deleted == 0,
        )
        .group_by(WorkoutRecord.workout_type)
    )
    return result.all()


async def create_training_plan(db: AsyncSession, coach_id: int, student_id: int, data: dict):
    """创建训练计划；coach_id=0 表示用户自建"""
    plan = TrainingPlan(coach_id=coach_id, student_id=student_id, **data)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_coach_students(db: AsyncSession, coach_id: int):
    """查询该教练名下所有绑定学员的基本信息"""
    result = await db.execute(
        select(User, CoachStudent)
        .join(CoachStudent, CoachStudent.student_id == User.id)
        .where(
            CoachStudent.coach_id == coach_id,
            CoachStudent.status == 1,
            User.is_deleted == 0,
        )
    )
    return result.all()


async def get_student_detail_for_coach(db: AsyncSession, coach_id: int, student_id: int):
    """查询学员详情（验证归属），返回 User 对象；不属于该教练则返回 None"""
    result = await db.execute(
        select(User)
        .join(CoachStudent, CoachStudent.student_id == User.id)
        .where(
            CoachStudent.coach_id == coach_id,
            CoachStudent.student_id == student_id,
            CoachStudent.status == 1,
            User.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def get_student_recent_records(db: AsyncSession, student_id: int, limit: int = 10):
    """查询学员最近 N 条训练记录"""
    result = await db.execute(
        select(WorkoutRecord)
        .where(WorkoutRecord.user_id == student_id, WorkoutRecord.is_deleted == 0)
        .order_by(WorkoutRecord.record_date.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_plans_by_student(db: AsyncSession, student_id: int):
    """查询某学员的全部训练计划（教练端用）"""
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.student_id == student_id, TrainingPlan.is_deleted == 0)
        .order_by(TrainingPlan.start_date.desc())
    )
    return result.scalars().all()
