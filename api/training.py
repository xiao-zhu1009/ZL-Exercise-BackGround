# api/training.py
# 用户端训练模块接口（需登录）
# GET    /training/records?start=&end=        查询训练记录列表
# POST   /training/records                    新增训练记录
# DELETE /training/records/{id}              删除训练记录
# GET    /training/plans?status=             查询训练计划列表
# POST   /training/plans                     用户自建训练计划
# GET    /training/stats?days=               近N天每日时长+卡路里统计
# GET    /training/stats/type?days=          近N天训练类型分布

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.training import WorkoutRecordCreate, TrainingPlanCreate
from CRUD.training import (
    get_workout_records, create_workout_record, delete_workout_record,
    get_training_plans, get_daily_stats, get_type_stats, create_training_plan,
)
from CRUD.user import get_user_by_id
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(tags=["training"])


@router.get("/training/records")
async def list_records(
    start: Optional[str] = None,
    end: Optional[str] = None,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询训练记录，默认近 30 天；start/end 均传时按区间查"""
    try:
        end_date   = date.fromisoformat(end)   if end   else date.today()
        start_date = date.fromisoformat(start) if start else end_date - timedelta(days=days - 1)
    except ValueError:
        return json_fail("日期格式错误，请使用 yyyy-MM-dd", 400)

    records = await get_workout_records(db, current_user["user_id"], start_date, end_date)
    return success([{
        "id":           r.id,
        "record_date":  r.record_date.isoformat(),
        "duration":     r.duration,
        "calories":     r.calories,
        "workout_type": r.workout_type,
        "note":         r.note,
    } for r in records])


@router.post("/training/records")
async def add_record(
    form: WorkoutRecordCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增一条训练记录"""
    if form.duration <= 0:
        return json_fail("训练时长必须大于 0", 400)
    if form.calories < 0:
        return json_fail("卡路里不能为负数", 400)
    if not form.workout_type.strip():
        return json_fail("训练类型不能为空", 400)

    record = await create_workout_record(db, current_user["user_id"], form.model_dump())
    return success({
        "id":           record.id,
        "record_date":  record.record_date.isoformat(),
        "duration":     record.duration,
        "calories":     record.calories,
        "workout_type": record.workout_type,
        "note":         record.note,
    }, "添加成功")


@router.delete("/training/records/{record_id}")
async def remove_record(
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除训练记录（软删除，仅本人可操作）"""
    ok = await delete_workout_record(db, record_id, current_user["user_id"])
    if not ok:
        return json_fail("记录不存在", 404)
    return success(None, "已删除")


@router.get("/training/plans")
async def list_plans(
    status: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户的训练计划列表，教练指派的计划附带教练昵称"""
    plans = await get_training_plans(db, current_user["user_id"], status)

    # 批量查教练昵称（coach_id=0 为自建，跳过）
    coach_ids = list({p.coach_id for p in plans if p.coach_id > 0})
    coach_map = {}
    for cid in coach_ids:
        u = await get_user_by_id(db, cid)
        if u:
            coach_map[cid] = u.nickname or u.username

    return success([{
        "id":           p.id,
        "title":        p.title,
        "goal":         p.goal,
        "start_date":   p.start_date.isoformat(),
        "end_date":     p.end_date.isoformat(),
        "description":  p.description,
        "content":      p.content,
        "status":       p.status,
        "coach_id":     p.coach_id,
        "coach_name":   coach_map.get(p.coach_id, "") if p.coach_id > 0 else "",
    } for p in plans])


@router.get("/training/plans/{plan_id}")
async def get_plan_detail(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询单个训练计划详情（仅本人可查）"""
    from sqlalchemy import select
    from models.training import TrainingPlan
    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.id == plan_id,
            TrainingPlan.student_id == current_user["user_id"],
            TrainingPlan.is_deleted == 0,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return json_fail("计划不存在", 404)

    coach_name = ""
    if plan.coach_id > 0:
        u = await get_user_by_id(db, plan.coach_id)
        if u:
            coach_name = u.nickname or u.username

    return success({
        "id":          plan.id,
        "title":       plan.title,
        "goal":        plan.goal,
        "start_date":  plan.start_date.isoformat(),
        "end_date":    plan.end_date.isoformat(),
        "description": plan.description,
        "content":     plan.content,
        "status":      plan.status,
        "coach_id":    plan.coach_id,
        "coach_name":  coach_name,
    })


@router.post("/training/plans")
async def add_plan(
    form: TrainingPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户自建训练计划（coach_id=0 标记为自建）"""
    if form.end_date < form.start_date:
        return json_fail("结束日期不能早于开始日期", 400)
    data = form.model_dump(exclude={"student_id"})
    plan = await create_training_plan(db, coach_id=0, student_id=current_user["user_id"], data=data)
    return success({
        "id":         plan.id,
        "title":      plan.title,
        "goal":       plan.goal,
        "start_date": plan.start_date.isoformat(),
        "end_date":   plan.end_date.isoformat(),
        "status":     plan.status,
    }, "计划创建成功")


@router.get("/training/stats")
async def daily_stats(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """近 N 天每日训练时长+卡路里汇总，补全无记录日期为 0"""
    if days < 1 or days > 90:
        return json_fail("days 范围 1~90", 400)

    end_date   = date.today()
    start_date = end_date - timedelta(days=days - 1)
    rows = await get_daily_stats(db, current_user["user_id"], start_date, end_date)

    data_map = {r.record_date.isoformat(): r for r in rows}
    result = []
    cur = start_date
    while cur <= end_date:
        key = cur.isoformat()
        r = data_map.get(key)
        result.append({
            "date":     key,
            "duration": int(r.duration) if r else 0,
            "calories": int(r.calories) if r else 0,
        })
        cur += timedelta(days=1)
    return success(result)


@router.get("/training/stats/type")
async def type_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """近 N 天训练类型分布，用于饼图"""
    if days < 1 or days > 365:
        return json_fail("days 范围 1~365", 400)

    end_date   = date.today()
    start_date = end_date - timedelta(days=days - 1)
    rows = await get_type_stats(db, current_user["user_id"], start_date, end_date)
    return success([{"name": r.workout_type, "value": r.count} for r in rows])
