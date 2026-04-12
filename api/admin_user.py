# api/admin_user.py
# 超管用户管理：列表查询、封禁/解封、角色变更（降级/升级）

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from db.session import get_db
from models.user import User
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/admin", tags=["admin-user"])


def _require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    return current_user


class StatusForm(BaseModel):
    status: int  # 0=封禁 1=启用


class RoleForm(BaseModel):
    role: str  # user / coach


@router.get("/users")
async def list_users(
    keyword: str = "",
    role: str = "",
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """用户列表，支持关键词（用户名/昵称）和角色筛选"""
    q = select(User).where(User.is_deleted == 0, User.role != "admin")
    if keyword:
        q = q.where(or_(User.username.contains(keyword), User.nickname.contains(keyword)))
    if role:
        q = q.where(User.role == role)
    result = await db.execute(q.order_by(User.id.desc()))
    users = result.scalars().all()
    return success({
        "list": [
            {
                "id": u.id,
                "username": u.username,
                "nickname": u.nickname,
                "role": u.role,
                "status": u.status,
                "created_at": str(u.created_at)[:10],
            }
            for u in users
        ],
        "total": len(users),
    })


@router.put("/users/{user_id}/status")
async def update_status(
    user_id: int,
    form: StatusForm,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """封禁或解封用户（不可操作管理员）"""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
    user = result.scalar_one_or_none()
    if not user:
        return json_fail("用户不存在", 404)
    if user.role == "admin":
        return json_fail("不可操作管理员账号", 403)
    if form.status not in (0, 1):
        return json_fail("status 只能为 0 或 1", 400)

    user.status = form.status
    # 封禁时清除 token，使其立即下线
    if form.status == 0:
        user.token = ""
    await db.commit()
    return success(None, "封禁成功" if form.status == 0 else "已解封")


@router.put("/users/{user_id}/role")
async def update_role(
    user_id: int,
    form: RoleForm,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """变更用户角色（仅允许 user ↔ coach，不可操作管理员）"""
    if form.role not in ("user", "coach"):
        return json_fail("角色只能设为 user 或 coach", 400)
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
    user = result.scalar_one_or_none()
    if not user:
        return json_fail("用户不存在", 404)
    if user.role == "admin":
        return json_fail("不可操作管理员账号", 403)

    user.role = form.role
    # 角色变更后清除 token，要求重新登录以获取新角色
    user.token = ""
    # 降级为普通用户时，将已通过的教练申请标记为 revoked，避免申请页仍显示"已通过"
    if form.role == "user":
        from models.coach_application import CoachApplication
        app_result = await db.execute(
            select(CoachApplication).where(
                CoachApplication.user_id == user_id,
                CoachApplication.status == "approved",
                CoachApplication.is_deleted == 0,
            )
        )
        approved_app = app_result.scalar_one_or_none()
        if approved_app:
            approved_app.status = "revoked"
    await db.commit()
    return success(None, "角色已更新")
