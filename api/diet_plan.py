# api/diet_plan.py
# 饮食计划接口
# 教练端：POST /coach/diet-plans          为学员创建饮食计划
#         GET  /coach/diet-plans          查询为某学员制定的计划列表 ?student_id=
#         PUT  /coach/diet-plans/{id}/status  更新计划状态
# 学员端：GET  /diet-plans               查询教练制定的饮食计划列表 ?status=
#         GET  /diet-plans/{id}          查询单条饮食计划详情
#         POST /diet-plans/self          学员创建自拟饮食计划
#         GET  /diet-plans/self          查询自拟饮食计划列表 ?status=
#         PUT  /diet-plans/self/{id}/status  更新自拟计划状态

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from utils.deps import get_current_user
from utils.response import success, json_fail
from schemas.diet_plan import DietPlanCreate, DietPlanStatusUpdate, SelfDietPlanCreate
from CRUD.diet_plan import (
    create_diet_plan, get_diet_plans_for_student,
    get_diet_plan_by_id, get_diet_plans_by_coach_student,
    update_diet_plan_status, create_self_diet_plan, get_self_diet_plans,
)
from CRUD.training import get_student_detail_for_coach
from CRUD.user import get_user_by_id
from typing import Optional

router = APIRouter(tags=["diet-plan"])


def _require_coach(current_user: dict):
    if current_user["role"] != "coach":
        return json_fail("无权限，仅教练可操作", 403)
    return None


def _plan_dict(plan, coach_name: str = "") -> dict:
    return {
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
    }


# ── 教练端 ────────────────────────────────────────────────

@router.post("/coach/diet-plans")
async def create_plan(
    form: DietPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练为学员创建饮食计划"""
    err = _require_coach(current_user)
    if err:
        return err

    if form.end_date < form.start_date:
        return json_fail("结束日期不能早于开始日期", 400)

    # 验证学员归属
    student = await get_student_detail_for_coach(db, current_user["user_id"], form.student_id)
    if not student:
        return json_fail("学员不存在或不属于该教练", 404)

    data = form.model_dump(exclude={"student_id"})
    plan = await create_diet_plan(db, current_user["user_id"], form.student_id, data)
    return success({"id": plan.id}, "饮食计划创建成功")


@router.get("/coach/diet-plans")
async def list_plans_for_student(
    student_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练查询为某学员制定的饮食计划列表"""
    err = _require_coach(current_user)
    if err:
        return err

    student = await get_student_detail_for_coach(db, current_user["user_id"], student_id)
    if not student:
        return json_fail("学员不存在或不属于该教练", 404)

    plans = await get_diet_plans_by_coach_student(db, current_user["user_id"], student_id)
    return success([_plan_dict(p) for p in plans])


@router.put("/coach/diet-plans/{plan_id}/status")
async def update_plan_status(
    plan_id: int,
    form: DietPlanStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练更新饮食计划状态（0=终止 2=完成）"""
    err = _require_coach(current_user)
    if err:
        return err

    if form.status not in (0, 2):
        return json_fail("status 只允许 0（终止）或 2（完成）", 400)

    plan = await get_diet_plan_by_id(db, plan_id)
    if not plan or plan.coach_id != current_user["user_id"]:
        return json_fail("计划不存在", 404)

    await update_diet_plan_status(db, plan, form.status)
    return success(None, "已更新")


# ── 学员端（教练制定） ─────────────────────────────────────

@router.get("/diet-plans")
async def student_list_plans(
    status: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员查询教练制定的饮食计划列表（含教练昵称）"""
    plans = await get_diet_plans_for_student(db, current_user["user_id"], status)

    coach_ids = list({p.coach_id for p in plans})
    coach_map = {}
    for cid in coach_ids:
        u = await get_user_by_id(db, cid)
        if u:
            coach_map[cid] = u.nickname or u.username

    return success([_plan_dict(p, coach_map.get(p.coach_id, "")) for p in plans])


@router.get("/diet-plans/self")
async def student_list_self_plans(
    status: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员查询自拟饮食计划列表"""
    plans = await get_self_diet_plans(db, current_user["user_id"], status)
    return success([_plan_dict(p) for p in plans])


@router.post("/diet-plans/self")
async def student_create_self_plan(
    form: SelfDietPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员创建自拟饮食计划"""
    if form.end_date < form.start_date:
        return json_fail("结束日期不能早于开始日期", 400)

    data = form.model_dump()
    plan = await create_self_diet_plan(db, current_user["user_id"], data)
    return success({"id": plan.id}, "自拟计划创建成功")


@router.put("/diet-plans/self/{plan_id}/status")
async def student_update_self_plan_status(
    plan_id: int,
    form: DietPlanStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员更新自拟饮食计划状态（0=终止 2=完成）"""
    if form.status not in (0, 2):
        return json_fail("status 只允许 0（终止）或 2（完成）", 400)

    plan = await get_diet_plan_by_id(db, plan_id)
    # coach_id=0 且归属当前学员才允许操作
    if not plan or plan.coach_id != 0 or plan.student_id != current_user["user_id"]:
        return json_fail("计划不存在", 404)

    await update_diet_plan_status(db, plan, form.status)
    return success(None, "已更新")


@router.get("/diet-plans/{plan_id}")
async def student_get_plan(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员查询单条饮食计划详情"""
    plan = await get_diet_plan_by_id(db, plan_id)
    if not plan or plan.student_id != current_user["user_id"]:
        return json_fail("计划不存在", 404)

    coach_name = ""
    if plan.coach_id != 0:
        u = await get_user_by_id(db, plan.coach_id)
        if u:
            coach_name = u.nickname or u.username

    return success(_plan_dict(plan, coach_name))
