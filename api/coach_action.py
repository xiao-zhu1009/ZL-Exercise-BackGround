# api/coach_action.py
# 教练端动作投稿接口（需 coach 角色）
# POST   /coach/actions       → 发布新动作（status=0 待审核）
# GET    /coach/actions       → 查看我的全部投稿
# PUT    /coach/actions/{id}  → 修改被驳回的动作，重置为待审核
# DELETE /coach/actions/{id}  → 删除待审核或已驳回的动作

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.action import ActionCreate, ActionUpdate
from CRUD.action import (
    create_action, get_coach_actions,
    get_action_by_id, update_action, soft_delete_action,
)
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/coach/actions", tags=["coach-actions"])


# 角色校验：非 coach 直接返回 403，路由函数首行调用
def _require_coach(current_user: dict):
    if current_user.get("role") != "coach":
        return json_fail("无权限", 403)


@router.post("")
async def publish_action(
    form: ActionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布新动作，初始状态为待审核"""
    err = _require_coach(current_user)
    if err:
        return err
    action = await create_action(db, current_user["user_id"], form.model_dump())
    return success({"id": action.id}, "提交成功，等待审核")


@router.get("")
async def my_actions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我投稿的全部动作"""
    err = _require_coach(current_user)
    if err:
        return err
    actions = await get_coach_actions(db, current_user["user_id"])
    return success([{
        "id": a.id,
        "title": a.title,
        "body_part": a.body_part,
        "category": a.category,
        "difficulty": a.difficulty,
        "status": a.status,
        "reject_reason": a.reject_reason,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for a in actions])


@router.put("/{action_id}")
async def edit_action(
    action_id: int,
    form: ActionUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改被驳回的动作并重新提交审核"""
    err = _require_coach(current_user)
    if err:
        return err
    action = await get_action_by_id(db, action_id)
    if not action or action.author_id != current_user["user_id"]:
        return json_fail("动作不存在", 404)
    if action.status != 2:
        return json_fail("只能修改已驳回的动作", 400)
    await update_action(db, action, form.model_dump(exclude_unset=True))
    return success(None, "已重新提交审核")


@router.delete("/{action_id}")
async def delete_action(
    action_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除待审核或已驳回的动作"""
    err = _require_coach(current_user)
    if err:
        return err
    action = await get_action_by_id(db, action_id)
    if not action or action.author_id != current_user["user_id"]:
        return json_fail("动作不存在", 404)
    if action.status not in (0, 2):
        return json_fail("只能删除待审核或已驳回的动作", 400)
    await soft_delete_action(db, action)
    return success(None, "已删除")
