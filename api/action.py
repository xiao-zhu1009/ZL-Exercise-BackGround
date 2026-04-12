# api/action.py
# 用户端动作库接口（无需登录）
# GET /actions        → 已上线动作列表，支持 body_part/category/difficulty/keyword 筛选
# GET /actions/{id}   → 动作详情，同时触发浏览数 +1

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from CRUD.action import get_actions, get_action_by_id, increment_view
from CRUD.user import get_user_by_id
from utils.response import success, json_fail

router = APIRouter(prefix="/actions", tags=["actions"])


# 详情响应组装：列表页只用部分字段，详情页用此函数
def _fmt(action, author_name=""):
    return {
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
        "view_count": action.view_count,
        "author_name": author_name,
        "created_at": action.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("")
async def list_actions(
    body_part: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """获取已上线动作列表，支持筛选和分页"""
    actions, total = await get_actions(db, body_part, category, difficulty, keyword, page, page_size)
    return success({
        "list": [{
            "id": a.id,
            "title": a.title,
            "body_part": a.body_part,
            "category": a.category,
            "difficulty": a.difficulty,
            "cover_img": a.cover_img,
            "view_count": a.view_count,
        } for a in actions],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{action_id}")
async def action_detail(action_id: int, db: AsyncSession = Depends(get_db)):
    """获取动作详情，浏览数 +1"""
    action = await get_action_by_id(db, action_id)
    if not action or action.status != 1:
        return json_fail("动作不存在", 404)

    await increment_view(db, action_id)

    author = await get_user_by_id(db, action.author_id)
    return success(_fmt(action, author.nickname if author else ""))
