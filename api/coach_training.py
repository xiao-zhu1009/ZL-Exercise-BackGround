# api/coach_training.py
# 教练端训练模块接口（需教练角色）
# GET  /coach/students                    查询名下学员列表
# GET  /coach/students/{id}              查询学员详情（含最近训练记录）
# POST /coach/training/plans             为学员创建训练计划
# GET  /coach/training/plans?student_id= 查询某学员的训练计划列表

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models.training import WorkoutRecord
from schemas.training import TrainingPlanCreate
from CRUD.training import (
    create_training_plan, get_coach_students,
    get_student_detail_for_coach, get_student_recent_records, get_plans_by_student,
)
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(tags=["coach-training"])


def _require_coach(current_user: dict):
    """角色校验：非教练直接返回 403 响应体（由调用方 return）"""
    if current_user["role"] != "coach":
        return json_fail("无权限，仅教练可操作", 403)
    return None


@router.get("/coach/students")
async def list_students(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询该教练名下所有绑定学员"""
    err = _require_coach(current_user)
    if err:
        return err

    rows = await get_coach_students(db, current_user["user_id"])
    result = []
    for user, cs in rows:
        result.append({
            "id":       user.id,
            "nickname": user.nickname or user.username,
            "goal":     user.goal or "",
            "bind_at":  cs.bind_at.isoformat() if cs.bind_at else "",
        })
    return success(result)


@router.get("/coach/students/{student_id}")
async def student_detail(
    student_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询学员详情（含最近10条训练记录），验证归属"""
    err = _require_coach(current_user)
    if err:
        return err

    user = await get_student_detail_for_coach(db, current_user["user_id"], student_id)
    if not user:
        return json_fail("学员不存在或不属于该教练", 404)

    records = await get_student_recent_records(db, student_id)
    return success({
        "id":       user.id,
        "nickname": user.nickname or user.username,
        "goal":     user.goal or "",
        "workout_records": [{
            "record_date":  r.record_date.isoformat(),
            "workout_type": r.workout_type,
            "duration":     r.duration,
            "calories":     r.calories,
        } for r in records],
    })


@router.post("/coach/training/plans")
async def create_plan_for_student(
    form: TrainingPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练为指定学员创建训练计划"""
    err = _require_coach(current_user)
    if err:
        return err

    if not form.student_id:
        return json_fail("student_id 不能为空", 400)
    if form.end_date < form.start_date:
        return json_fail("结束日期不能早于开始日期", 400)

    # 验证学员归属，防止越权
    user = await get_student_detail_for_coach(db, current_user["user_id"], form.student_id)
    if not user:
        return json_fail("学员不存在或不属于该教练", 404)

    data = form.model_dump(exclude={"student_id"})
    plan = await create_training_plan(db, coach_id=current_user["user_id"], student_id=form.student_id, data=data)
    return success({
        "id":         plan.id,
        "title":      plan.title,
        "goal":       plan.goal,
        "start_date": plan.start_date.isoformat(),
        "end_date":   plan.end_date.isoformat(),
        "status":     plan.status,
    }, "计划创建成功")


@router.get("/coach/training/plans")
async def list_plans_for_student(
    student_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询某学员的全部训练计划"""
    err = _require_coach(current_user)
    if err:
        return err

    user = await get_student_detail_for_coach(db, current_user["user_id"], student_id)
    if not user:
        return json_fail("学员不存在或不属于该教练", 404)

    plans = await get_plans_by_student(db, student_id)
    return success([{
        "id":          p.id,
        "title":       p.title,
        "goal":        p.goal,
        "start_date":  p.start_date.isoformat(),
        "end_date":    p.end_date.isoformat(),
        "description": p.description,
        "status":      p.status,
        "coach_id":    p.coach_id,   # 0=学员自建，否则为教练id
    } for p in plans])
