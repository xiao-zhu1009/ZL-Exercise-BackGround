# api/coach_bind.py
# 教练-学员绑定模块接口
# 用户端：GET /coaches 教练列表；POST /coach-bind/apply 申请绑定；GET /coach-bind/my 我的绑定状态；DELETE /coach-bind/me 解绑
# 教练端：GET /coach/bind-requests 申请列表；POST /coach/bind-requests/{id}/approve 同意；POST /coach/bind-requests/{id}/reject 拒绝
# 管理员：GET /admin/coach-bind/stats 统计看板；GET /admin/coach-bind/coaches 教练维度统计

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from utils.deps import get_current_user
from utils.response import success, fail, json_fail
from CRUD.training import (
    get_coaches_list, get_bind_record, create_bind_request,
    get_my_coach, get_my_pending_apply, get_student_bind_requests, handle_bind_request,
    end_bind, get_bind_stats_for_admin, get_coach_summary_for_admin,
)

router = APIRouter(tags=["coach-bind"])


class BindApplyForm(BaseModel):
    coach_id: int
    request_msg: Optional[str] = ""


class RejectBindForm(BaseModel):
    reject_reason: Optional[str] = ""


# ── 用户端 ────────────────────────────────────────────────
# 获取教练数据接口
@router.get("/coaches")
async def list_coaches(
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """公开：教练列表，支持关键词搜索（无需登录）"""
    coaches, total = await get_coaches_list(db, keyword, page, page_size)
    return success({
        "list": [{
            "id":        c.id,
            "nickname":  c.nickname or c.username,
            "avatar":    c.avatar,
            "signature": c.signature,
        } for c in coaches],
        "total": total,
        "page": page,
        "page_size": page_size,
    })

# 用户端申请绑定教练接口
@router.post("/coach-bind/apply")
async def apply_bind(
    form: BindApplyForm,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员申请绑定教练；同一对关系只能有一条 pending/active 记录"""
    student_id = current_user["user_id"]

    # 不能绑定自己
    if form.coach_id == student_id:
        return fail("不能绑定自己", 4001)

    existing = await get_bind_record(db, form.coach_id, student_id)
    if existing:
        if existing.status == "active":
            return fail("您已绑定该教练", 4002)
        if existing.status == "pending":
            return fail("申请已提交，请等待教练处理", 4003)
        # ended/rejected 允许重新申请：更新记录
        existing.status = "pending"
        existing.request_msg = form.request_msg or ""
        existing.reject_reason = ""
        from db.session import AsyncSessionLocal
        await db.commit()
        return success({"id": existing.id}, "申请已重新提交")

    record = await create_bind_request(db, form.coach_id, student_id, form.request_msg or "")
    return success({"id": record.id}, "申请已提交")


@router.get("/coach-bind/my")
async def my_bind(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前学员的绑定状态：active 绑定 + pending 申请（前端用于渲染按钮状态）"""
    student_id = current_user["user_id"]

    active_row = await get_my_coach(db, student_id)
    pending_row = await get_my_pending_apply(db, student_id)

    active_info = None
    if active_row:
        coach, cs = active_row
        active_info = {
            "coach_id":  coach.id,
            "nickname":  coach.nickname or coach.username,
            "avatar":    coach.avatar,
            "signature": coach.signature,
            "bind_at":   cs.bind_at.isoformat() if cs.bind_at else "",
            "bind_id":   cs.id,
        }

    pending_info = None
    if pending_row:
        coach, cs = pending_row
        pending_info = {
            "coach_id":  coach.id,
            "nickname":  coach.nickname or coach.username,
            "bind_id":   cs.id,
        }

    return success({
        "active":  active_info,   # 当前绑定的教练，无则 null
        "pending": pending_info,  # 待处理的申请，无则 null
    })


@router.delete("/coach-bind/me")
async def unbind(
    bind_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学员主动解绑（仅限 active 状态）"""
    from sqlalchemy import select
    from models.training import CoachStudent
    result = await db.execute(
        select(CoachStudent).where(
            CoachStudent.id == bind_id,
            CoachStudent.student_id == current_user["user_id"],
            CoachStudent.status == "active",
            CoachStudent.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return json_fail("绑定记录不存在或已解绑", 404)
    await end_bind(db, record)
    return success(None, "已解绑")


# ── 教练端 ────────────────────────────────────────────────

@router.get("/coach/bind-requests")
async def list_bind_requests(
    status: Optional[str] = None,  # pending / active / rejected / ended
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练端：查看收到的绑定申请列表"""
    if current_user["role"] != "coach":
        return json_fail("无权限", 403)
    rows = await get_student_bind_requests(db, current_user["user_id"], status)
    return success([{
        "bind_id":      cs.id,
        "student_id":   u.id,
        "nickname":     u.nickname or u.username,
        "avatar":       u.avatar,
        "status":       cs.status,
        "request_msg":  cs.request_msg,
        "reject_reason": cs.reject_reason,
        "bind_at":      cs.bind_at.isoformat() if cs.bind_at else "",
        "created_at":   cs.created_at.isoformat(),
    } for cs, u in rows])


@router.post("/coach/bind-requests/{bind_id}/approve")
async def approve_bind(
    bind_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练同意绑定申请"""
    if current_user["role"] != "coach":
        return json_fail("无权限", 403)

    from sqlalchemy import select
    from models.training import CoachStudent
    result = await db.execute(
        select(CoachStudent).where(
            CoachStudent.id == bind_id,
            CoachStudent.coach_id == current_user["user_id"],
            CoachStudent.status == "pending",
            CoachStudent.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return json_fail("申请不存在或已处理", 404)
    await handle_bind_request(db, record, "approve")
    return success(None, "已同意")


@router.post("/coach/bind-requests/{bind_id}/reject")
async def reject_bind(
    bind_id: int,
    form: RejectBindForm,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练拒绝绑定申请"""
    if current_user["role"] != "coach":
        return json_fail("无权限", 403)

    from sqlalchemy import select
    from models.training import CoachStudent
    result = await db.execute(
        select(CoachStudent).where(
            CoachStudent.id == bind_id,
            CoachStudent.coach_id == current_user["user_id"],
            CoachStudent.status == "pending",
            CoachStudent.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return json_fail("申请不存在或已处理", 404)
    await handle_bind_request(db, record, "reject", form.reject_reason or "")
    return success(None, "已拒绝")


@router.delete("/coach/bind-requests/{bind_id}/end")
async def coach_end_bind(
    bind_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练主动解绑学员（仅限 active 状态）"""
    if current_user["role"] != "coach":
        return json_fail("无权限", 403)

    from sqlalchemy import select
    from models.training import CoachStudent
    result = await db.execute(
        select(CoachStudent).where(
            CoachStudent.id == bind_id,
            CoachStudent.coach_id == current_user["user_id"],
            CoachStudent.status == "active",
            CoachStudent.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return json_fail("绑定记录不存在或已解绑", 404)
    await end_bind(db, record)
    return success(None, "已解绑")


# ── 管理员端 ──────────────────────────────────────────────

@router.get("/admin/coach-bind/stats")
async def bind_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员：绑定关系总览统计"""
    if current_user["role"] != "admin":
        return json_fail("无权限", 403)
    stats = await get_bind_stats_for_admin(db)
    return success(stats)


@router.get("/admin/coach-bind/coaches")
async def coach_summary(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员：教练维度统计（名下学员数、下发计划数）"""
    if current_user["role"] != "admin":
        return json_fail("无权限", 403)
    data, total = await get_coach_summary_for_admin(db, page, page_size)
    return success({"list": data, "total": total, "page": page, "page_size": page_size})
