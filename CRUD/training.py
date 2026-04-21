# CRUD/training.py
# 训练模块数据层：训练记录增删查、训练计划增查、教练学员查询、统计图表数据

from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.training import BodyRecord, TrainingRecord, TrainingPlan, CoachStudent
from models.user import User


# ── 身体记录 ──────────────────────────────────────────────────

async def get_body_records(db: AsyncSession, user_id: int, days: int = 90):
    """查询用户近 N 天的身体记录，按日期升序（用于图表）"""
    start = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(BodyRecord)
        .where(BodyRecord.user_id == user_id, BodyRecord.record_date >= start, BodyRecord.is_deleted == 0)
        .order_by(BodyRecord.record_date.asc())
    )
    return result.scalars().all()


async def get_latest_body_record(db: AsyncSession, user_id: int):
    """查询用户最近一条身体记录，新增时用于预填数据"""
    result = await db.execute(
        select(BodyRecord)
        .where(BodyRecord.user_id == user_id, BodyRecord.is_deleted == 0)
        .order_by(BodyRecord.record_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_body_record(db: AsyncSession, user_id: int, data: dict):
    """新增一条身体记录"""
    record = BodyRecord(user_id=user_id, **data)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_body_record(db: AsyncSession, record_id: int, user_id: int, data: dict):
    """更新身体记录，仅本人可操作"""
    result = await db.execute(
        select(BodyRecord).where(BodyRecord.id == record_id, BodyRecord.user_id == user_id, BodyRecord.is_deleted == 0)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None
    for k, v in data.items():
        setattr(record, k, v)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_body_record(db: AsyncSession, record_id: int, user_id: int) -> bool:
    """软删除身体记录，仅本人可操作"""
    result = await db.execute(
        select(BodyRecord).where(BodyRecord.id == record_id, BodyRecord.user_id == user_id, BodyRecord.is_deleted == 0)
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    record.is_deleted = 1
    await db.commit()
    return True


# ── 训练记录 ──────────────────────────────────────────────────

async def get_workout_records(db: AsyncSession, user_id: int, start: date, end: date):
    """查询用户指定日期区间内的训练记录，按日期倒序"""
    result = await db.execute(
        select(TrainingRecord)
        .where(
            TrainingRecord.user_id == user_id,
            TrainingRecord.record_date >= start,
            TrainingRecord.record_date <= end,
            TrainingRecord.is_deleted == 0,
        )
        .order_by(TrainingRecord.record_date.desc())
    )
    return result.scalars().all()


async def create_workout_record(db: AsyncSession, user_id: int, data: dict):
    """新增一条训练记录"""
    record = TrainingRecord(user_id=user_id, **data)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_workout_record(db: AsyncSession, record_id: int, user_id: int, data: dict):
    """更新训练记录，仅本人可操作；返回更新后的对象，不存在则返回 None"""
    result = await db.execute(
        select(TrainingRecord).where(
            TrainingRecord.id == record_id,
            TrainingRecord.user_id == user_id,
            TrainingRecord.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return None
    for k, v in data.items():
        setattr(record, k, v)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_workout_record(db: AsyncSession, record_id: int, user_id: int) -> bool:
    """软删除训练记录，仅本人可操作"""
    result = await db.execute(
        select(TrainingRecord).where(
            TrainingRecord.id == record_id,
            TrainingRecord.user_id == user_id,
            TrainingRecord.is_deleted == 0,
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
            TrainingRecord.record_date,
            func.sum(TrainingRecord.duration).label("duration"),
            func.sum(TrainingRecord.calories).label("calories"),
        )
        .where(
            TrainingRecord.user_id == user_id,
            TrainingRecord.record_date >= start,
            TrainingRecord.record_date <= end,
            TrainingRecord.is_deleted == 0,
        )
        .group_by(TrainingRecord.record_date)
        .order_by(TrainingRecord.record_date)
    )
    return result.all()


async def get_type_stats(db: AsyncSession, user_id: int, start: date, end: date):
    """按训练类型汇总次数，用于饼图"""
    result = await db.execute(
        select(
            TrainingRecord.workout_type,
            func.count(TrainingRecord.id).label("count"),
        )
        .where(
            TrainingRecord.user_id == user_id,
            TrainingRecord.record_date >= start,
            TrainingRecord.record_date <= end,
            TrainingRecord.is_deleted == 0,
        )
        .group_by(TrainingRecord.workout_type)
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
        select(TrainingRecord)
        .where(TrainingRecord.user_id == student_id, TrainingRecord.is_deleted == 0)
        .order_by(TrainingRecord.record_date.desc())
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


async def get_body_records_recent(db: AsyncSession, user_id: int, days: int = 30):
    """查询用户近 N 天的体重记录，按日期升序"""
    start = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(BodyRecord)
        .where(
            BodyRecord.user_id == user_id,
            BodyRecord.record_date >= start,
            BodyRecord.is_deleted == 0,
        )
        .order_by(BodyRecord.record_date.asc())
    )
    return result.scalars().all()


async def get_dashboard_stats(db: AsyncSession, user_id: int):
    """看板聚合查询：本周训练统计、今日饮食、体重趋势、训练趋势、类型分布、热量趋势"""
    from models.diet import DietRecord

    today = date.today()
    # 本周周一
    week_start = today - timedelta(days=today.weekday())

    # 1. 本周训练次数 + 消耗卡路里
    week_workout = await db.execute(
        select(
            func.count(TrainingRecord.id).label("count"),
            func.coalesce(func.sum(TrainingRecord.calories), 0).label("calories"),
        ).where(
            TrainingRecord.user_id == user_id,
            TrainingRecord.record_date >= week_start,
            TrainingRecord.record_date <= today,
            TrainingRecord.is_deleted == 0,
        )
    )
    ww = week_workout.first()

    # 2. 今日摄入卡路里
    today_diet = await db.execute(
        select(func.coalesce(func.sum(DietRecord.calories), 0)).where(
            DietRecord.user_id == user_id,
            DietRecord.record_date == today,
            DietRecord.is_deleted == 0,
        )
    )
    calories_today = today_diet.scalar() or 0

    # 3. 近 30 天体重记录
    body_rows = await get_body_records_recent(db, user_id, 30)

    # 4. 本周每天训练时长（周一~今天，补全 0）
    week_daily = await db.execute(
        select(
            TrainingRecord.record_date,
            func.sum(TrainingRecord.duration).label("duration"),
            func.sum(TrainingRecord.calories).label("calories"),
        ).where(
            TrainingRecord.user_id == user_id,
            TrainingRecord.record_date >= week_start,
            TrainingRecord.record_date <= today,
            TrainingRecord.is_deleted == 0,
        ).group_by(TrainingRecord.record_date)
    )
    week_daily_map = {r.record_date: r for r in week_daily.all()}

    day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    workout_week = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        r = week_daily_map.get(d)
        workout_week.append({
            "date": d.isoformat(),
            "day": day_labels[i],
            "duration": int(r.duration) if r else 0,
            "calories": int(r.calories) if r else 0,
        })

    # 5. 近 30 天训练类型分布
    type_rows = await db.execute(
        select(
            TrainingRecord.workout_type,
            func.count(TrainingRecord.id).label("count"),
        ).where(
            TrainingRecord.user_id == user_id,
            TrainingRecord.record_date >= today - timedelta(days=29),
            TrainingRecord.is_deleted == 0,
        ).group_by(TrainingRecord.workout_type)
    )
    workout_type_stats = [
        {"type": r.workout_type or "其他", "count": r.count}
        for r in type_rows.all()
    ]

    # 6. 近 7 天每日热量摄入（补全 0）
    diet_start = today - timedelta(days=6)
    diet_rows = await db.execute(
        select(
            DietRecord.record_date,
            func.sum(DietRecord.calories).label("calories"),
        ).where(
            DietRecord.user_id == user_id,
            DietRecord.record_date >= diet_start,
            DietRecord.record_date <= today,
            DietRecord.is_deleted == 0,
        ).group_by(DietRecord.record_date)
    )
    diet_map = {r.record_date: float(r.calories) for r in diet_rows.all()}
    diet_week = []
    for i in range(7):
        d = diet_start + timedelta(days=i)
        diet_week.append({"date": d.isoformat(), "calories": round(diet_map.get(d, 0), 1)})

    # 最新体重
    current_weight = float(body_rows[-1].weight) if body_rows else None

    return {
        "workout_count_week":   int(ww.count),
        "calories_burned_week": int(ww.calories),
        "calories_intake_today": round(float(calories_today), 1),
        "current_weight":       current_weight,
        "body_records": [
            {"date": r.record_date.isoformat(), "weight": float(r.weight)}
            for r in body_rows if r.weight is not None
        ],
        "workout_week":        workout_week,
        "workout_type_stats":  workout_type_stats,
        "diet_week":           diet_week,
    }
