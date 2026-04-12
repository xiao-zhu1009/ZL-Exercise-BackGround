# api/admin_action.py
# 管理员动作审核接口（需 admin 角色）
# GET /admin/actions                  → 全部动作列表，可按 status 筛选
# GET /admin/actions/{id}/detail      → 单条动作完整详情（不限 status，供审核预览）
# PUT /admin/actions/{id}/review      → 审核：status=1 通过，status=2 驳回
# PUT /admin/actions/{id}/offline     → 下架已上线动作（status 改为 3）

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.action import ActionReview
from CRUD.action import get_admin_actions, get_action_by_id, review_action
from CRUD.user import get_user_by_id
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/admin/actions", tags=["admin-actions"])


# 角色校验：非 admin 直接返回 403，路由函数首行调用
def _require_admin(current_user: dict):
    if current_user.get("role") != "admin":
        return json_fail("无权限", 403)


@router.get("/{action_id}/detail")
async def action_detail(
    action_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员预览单条动作完整内容。
    与用户端详情接口的区别：不过滤 status，待审核/已驳回/已下架都能查到，
    且不触发 view_count +1（管理员预览不算用户浏览）。
    """
    err = _require_admin(current_user)
    if err:
        return err
    action = await get_action_by_id(db, action_id)
    if not action:
        return json_fail("动作不存在", 404)
    author = await get_user_by_id(db, action.author_id)
    return success({
        "id": action.id,
        "title": action.title,
        "body_part": action.body_part,
        "category": action.category,
        "difficulty": action.difficulty,
        "cover_img": action.cover_img,
        "video_url": action.video_url,
        "description": action.description,
        "steps": action.steps or [],
        "cautions": action.cautions or [],
        "status": action.status,
        "reject_reason": action.reject_reason,
        "author_name": author.nickname if author else "",
        "created_at": action.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })


@router.get("")
async def list_all_actions(
    status: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取全部动作列表，可按 status 筛选（0待审核 1已上线 2已驳回 3已下架）"""
    err = _require_admin(current_user)
    if err:
        return err
    rows, total = await get_admin_actions(db, status, page, page_size)
    return success({
        "list": [{
            "id": a.id,
            "title": a.title,
            "body_part": a.body_part,
            "category": a.category,
            "difficulty": a.difficulty,
            "status": a.status,
            "reject_reason": a.reject_reason,
            "author_id": a.author_id,
            "author_name": nickname or "",
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        } for a, nickname in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.put("/{action_id}/review")
async def review(
    action_id: int,
    form: ActionReview,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """审核动作：status=1 通过，status=2 驳回（驳回需填 reject_reason）"""
    err = _require_admin(current_user)
    if err:
        return err
    if form.status not in (1, 2):
        return json_fail("status 只能为 1(通过) 或 2(驳回)", 400)
    if form.status == 2 and not form.reject_reason:
        return json_fail("驳回必须填写原因", 400)

    action = await get_action_by_id(db, action_id)
    if not action:
        return json_fail("动作不存在", 404)
    if action.status != 0:
        return json_fail("只能审核待审核状态的动作", 400)

    await review_action(db, action, form.status, form.reject_reason, current_user["user_id"])
    msg = "已通过" if form.status == 1 else "已驳回"
    return success(None, msg)


@router.put("/{action_id}/offline")
async def offline_action(
    action_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下架已上线的动作"""
    err = _require_admin(current_user)
    if err:
        return err
    action = await get_action_by_id(db, action_id)
    if not action:
        return json_fail("动作不存在", 404)
    if action.status != 1:
        return json_fail("只能下架已上线的动作", 400)
    action.status = 3
    await db.commit()
    return success(None, "已下架")
