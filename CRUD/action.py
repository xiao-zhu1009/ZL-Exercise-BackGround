# CRUD/action.py
# 动作库数据库操作，路由层调用这里，不直接写 SQL
# 函数职责：
#   get_actions          → 用户端列表查询（筛选+分页）
#   get_action_by_id     → 按 ID 查单条
#   increment_view       → 浏览数原子 +1
#   create_action        → 教练新建动作
#   get_coach_actions    → 教练查自己的投稿
#   update_action        → 修改被驳回动作并重置为待审核
#   soft_delete_action   → 软删除
#   get_admin_actions    → 管理员查全部动作（含作者昵称 JOIN）
#   review_action        → 管理员审核（写入审核人/时间）

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from models.action import Action
from models.user import User


async def get_actions(db: AsyncSession, body_part=None, category=None,
                      difficulty=None, keyword=None, page=1, page_size=12):
    """用户端：获取已上线动作列表，支持筛选和分页"""
    where = [Action.status == 1, Action.is_deleted == 0]
    if body_part:
        where.append(Action.body_part == body_part)
    if category:
        where.append(Action.category == category)
    if difficulty:
        where.append(Action.difficulty == difficulty)
    if keyword:
        where.append(Action.title.contains(keyword))

    total = (await db.execute(select(func.count(Action.id)).where(*where))).scalar()

    result = await db.execute(
        select(Action).where(*where)
        .order_by(Action.view_count.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def get_action_by_id(db: AsyncSession, action_id: int):
    """按 ID 查动作（含软删除过滤）"""
    result = await db.execute(
        select(Action).where(Action.id == action_id, Action.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def increment_view(db: AsyncSession, action_id: int):
    """浏览数原子 +1"""
    await db.execute(
        update(Action).where(Action.id == action_id)
        .values(view_count=Action.view_count + 1)
    )
    await db.commit()


async def create_action(db: AsyncSession, author_id: int, data: dict):
    """教练创建动作，初始状态为待审核"""
    action = Action(author_id=author_id, **data)
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def get_coach_actions(db: AsyncSession, author_id: int):
    """教练查自己投稿的全部动作"""
    result = await db.execute(
        select(Action)
        .where(Action.author_id == author_id, Action.is_deleted == 0)
        .order_by(Action.created_at.desc())
    )
    return result.scalars().all()


async def update_action(db: AsyncSession, action: Action, fields: dict):
    """更新被驳回的动作，重置为待审核"""
    for k, v in fields.items():
        if v is not None:
            setattr(action, k, v)
    action.status = 0
    action.reject_reason = ""
    await db.commit()


async def soft_delete_action(db: AsyncSession, action: Action):
    """软删除"""
    action.is_deleted = 1
    await db.commit()


async def get_admin_actions(db: AsyncSession, status=None, page=1, page_size=20):
    """管理员查动作列表，含投稿教练昵称"""
    where = [Action.is_deleted == 0]
    if status is not None:
        where.append(Action.status == status)

    total = (await db.execute(select(func.count(Action.id)).where(*where))).scalar()

    result = await db.execute(
        select(Action, User.nickname)
        .join(User, Action.author_id == User.id)
        .where(*where)
        .order_by(Action.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return result.all(), total


async def review_action(db: AsyncSession, action: Action, status: int,
                        reject_reason: str, admin_id: int):
    """审核动作：通过(1) 或 驳回(2)"""
    action.status = status
    action.reject_reason = reject_reason or ""
    action.reviewed_by = admin_id
    action.reviewed_at = datetime.now()
    await db.commit()
