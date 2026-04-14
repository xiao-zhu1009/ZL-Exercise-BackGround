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
    """查询该教练名下所有绑定学员的基本信息（status=active）"""
    result = await db.execute(
        select(User, CoachStudent)
        .join(CoachStudent, CoachStudent.student_id == User.id)
        .where(
            CoachStudent.coach_id == coach_id,
            CoachStudent.status == "active",
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
            CoachStudent.status == "active",
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


# ── 教练-学员绑定 ──────────────────────────────────────────

async def get_coaches_list(db: AsyncSession, keyword: str = None, page: int = 1, page_size: int = 10):
    """查询教练列表（公开），支持昵称/用户名关键词搜索"""
    stmt = select(User).where(User.role == "coach", User.is_deleted == 0, User.status == 1)
    if keyword:
        stmt = stmt.where(
            (User.nickname.ilike(f"%{keyword}%")) | (User.username.ilike(f"%{keyword}%"))
        )
    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_bind_record(db: AsyncSession, coach_id: int, student_id: int):
    """查询两人之间的绑定记录（不限状态）"""
    result = await db.execute(
        select(CoachStudent).where(
            CoachStudent.coach_id == coach_id,
            CoachStudent.student_id == student_id,
            CoachStudent.is_deleted == 0,
        )
    )
    return result.scalar_one_or_none()


async def create_bind_request(db: AsyncSession, coach_id: int, student_id: int, request_msg: str = ""):
    """学员发起绑定申请，status=pending"""
    record = CoachStudent(coach_id=coach_id, student_id=student_id,
                          status="pending", request_msg=request_msg)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_my_coach(db: AsyncSession, student_id: int):
    """查询学员当前绑定的教练（status=active）"""
    result = await db.execute(
        select(User, CoachStudent)
        .join(CoachStudent, CoachStudent.coach_id == User.id)
        .where(
            CoachStudent.student_id == student_id,
            CoachStudent.status == "active",
            CoachStudent.is_deleted == 0,
            User.is_deleted == 0,
        )
    )
    return result.first()


async def get_my_pending_apply(db: AsyncSession, student_id: int):
    """查询学员当前待处理的绑定申请（status=pending），返回 (User, CoachStudent) 或 None"""
    result = await db.execute(
        select(User, CoachStudent)
        .join(CoachStudent, CoachStudent.coach_id == User.id)
        .where(
            CoachStudent.student_id == student_id,
            CoachStudent.status == "pending",
            CoachStudent.is_deleted == 0,
            User.is_deleted == 0,
        )
    )
    return result.first()


async def get_student_bind_requests(db: AsyncSession, coach_id: int, status: str = None):
    """教练端：查询收到的绑定申请，可按 status 筛选"""
    stmt = (
        select(CoachStudent, User)
        .join(User, User.id == CoachStudent.student_id)
        .where(CoachStudent.coach_id == coach_id, CoachStudent.is_deleted == 0)
    )
    if status:
        stmt = stmt.where(CoachStudent.status == status)
    stmt = stmt.order_by(CoachStudent.created_at.desc())
    result = await db.execute(stmt)
    return result.all()


async def handle_bind_request(db: AsyncSession, record: CoachStudent, action: str, reject_reason: str = ""):
    """教练处理申请：action=approve → active；action=reject → rejected"""
    from datetime import datetime
    if action == "approve":
        record.status = "active"
        record.bind_at = datetime.now()
    else:
        record.status = "rejected"
        record.reject_reason = reject_reason
    await db.commit()
    return record


async def end_bind(db: AsyncSession, record: CoachStudent):
    """解除绑定：status=ended"""
    record.status = "ended"
    await db.commit()


async def get_bind_stats_for_admin(db: AsyncSession):
    """管理员：绑定关系统计数据"""
    active = await db.execute(
        select(func.count()).where(CoachStudent.status == "active", CoachStudent.is_deleted == 0)
    )
    pending = await db.execute(
        select(func.count()).where(CoachStudent.status == "pending", CoachStudent.is_deleted == 0)
    )
    ended = await db.execute(
        select(func.count()).where(CoachStudent.status == "ended", CoachStudent.is_deleted == 0)
    )
    return {
        "active": active.scalar(),
        "pending": pending.scalar(),
        "ended": ended.scalar(),
    }


async def get_coach_summary_for_admin(db: AsyncSession, page: int = 1, page_size: int = 20):
    """管理员：教练维度统计（名下学员数、下发计划数）"""
    from sqlalchemy import distinct
    coaches_result = await db.execute(
        select(User).where(User.role == "coach", User.is_deleted == 0)
        .offset((page - 1) * page_size).limit(page_size)
    )
    coaches = coaches_result.scalars().all()
    total_result = await db.execute(
        select(func.count()).where(User.role == "coach", User.is_deleted == 0)
    )
    total = total_result.scalar()

    data = []
    for c in coaches:
        student_cnt = await db.execute(
            select(func.count()).where(
                CoachStudent.coach_id == c.id,
                CoachStudent.status == "active",
                CoachStudent.is_deleted == 0,
            )
        )
        plan_cnt = await db.execute(
            select(func.count()).where(
                TrainingPlan.coach_id == c.id,
                TrainingPlan.is_deleted == 0,
            )
        )
        data.append({
            "coach_id": c.id,
            "nickname": c.nickname or c.username,
            "student_count": student_cnt.scalar(),
            "plan_count": plan_cnt.scalar(),
        })
    return data, total
