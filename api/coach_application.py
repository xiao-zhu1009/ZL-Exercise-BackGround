# api/coach_application.py
# 教练申请路由：用户提交/查询申请；超管审批

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from utils.deps import get_current_user
from utils.response import success, json_fail
from schemas.coach_application import ApplyForm, RejectForm
from CRUD.coach_application import (
    get_pending_by_user, get_latest_by_user, create_application,
    get_application_by_id, get_applications, approve_application, reject_application,
)
from CRUD.user import get_user_by_id
from models.user import User

router = APIRouter(tags=["coach-application"])


# ── 用户端 ────────────────────────────────────────────────

@router.post("/coach-application/apply")
async def apply(form: ApplyForm, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """用户提交成为教练的申请"""
    user = await get_user_by_id(db, current_user["user_id"])
    if user.role == "coach":
        return json_fail("您已是教练，无需申请", 400)
    if await get_pending_by_user(db, user.id):
        return json_fail("您已有待审申请，请耐心等待", 400)
    app = await create_application(db, user.id, form.reason)
    return success({"id": app.id, "status": app.status, "created_at": str(app.created_at)}, "申请已提交")


@router.get("/coach-application/my")
async def my_application(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """查询自己最新一条申请状态"""
    app = await get_latest_by_user(db, current_user["user_id"])
    if not app:
        return success(None)
    return success({
        "id": app.id,
        "status": app.status,
        "reason": app.reason,
        "reject_reason": app.reject_reason,
        "created_at": str(app.created_at),
        "updated_at": str(app.updated_at),
    })


# ── 管理端 ────────────────────────────────────────────────

def _require_admin(current_user: dict = Depends(get_current_user)):
    """仅超管可访问"""
    if current_user.get("role") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    return current_user


@router.get("/admin/coach-applications")
async def list_applications(
    status: str = None,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理端：获取申请列表，可按 status 过滤"""
    apps = await get_applications(db, status)
    # 批量查申请人信息
    user_ids = list({a.user_id for a in apps})
    users_map = {}
    if user_ids:
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in result.scalars().all():
            users_map[u.id] = u

    data = []
    for a in apps:
        u = users_map.get(a.user_id)
        data.append({
            "id": a.id,
            "user_id": a.user_id,
            "username": u.username if u else "",
            "nickname": u.nickname if u else "",
            "status": a.status,
            "reason": a.reason,
            "reject_reason": a.reject_reason,
            "reviewed_by": a.reviewed_by,
            "created_at": str(a.created_at),
            "updated_at": str(a.updated_at),
        })
    return success(data)


@router.post("/admin/coach-applications/{app_id}/approve")
async def approve(app_id: int, current_user: dict = Depends(_require_admin), db: AsyncSession = Depends(get_db)):
    """通过申请，同时将用户 role 改为 coach"""
    app = await get_application_by_id(db, app_id)
    if not app:
        return json_fail("申请不存在", 404)
    if app.status != "pending":
        return json_fail("该申请已处理", 400)

    await approve_application(db, app, current_user["user_id"])

    # 更新用户角色
    user = await get_user_by_id(db, app.user_id)
    if user:
        user.role = "coach"
        await db.commit()

    return success(None, "已通过")


@router.post("/admin/coach-applications/{app_id}/reject")
async def reject(
    app_id: int,
    form: RejectForm,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """拒绝申请"""
    app = await get_application_by_id(db, app_id)
    if not app:
        return json_fail("申请不存在", 404)
    if app.status != "pending":
        return json_fail("该申请已处理", 400)

    await reject_application(db, app, current_user["user_id"], form.reject_reason)
    return success(None, "已拒绝")
