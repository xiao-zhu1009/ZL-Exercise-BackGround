# api/admin_diet_article.py
# 管理员饮食文章审核接口（需 admin 角色）
# GET /admin/diet/articles                  → 全部文章列表，可按 status 筛选
# GET /admin/diet/articles/{id}/detail      → 单条文章完整详情（不限 status，供审核预览）
# PUT /admin/diet/articles/{id}/review      → 审核：status=1 通过，status=2 驳回
# PUT /admin/diet/articles/{id}/offline     → 下架已上线文章（status 改为 3）

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.diet_article import ArticleReview
from CRUD.diet_article import get_admin_articles, get_article_by_id, review_article, offline_article
from CRUD.user import get_user_by_id
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/admin/diet/articles", tags=["admin-diet-articles"])


def _require_admin(current_user: dict):
    """非 admin 角色直接返回 403"""
    if current_user.get("role") != "admin":
        return json_fail("无权限", 403)


@router.get("")
async def list_all_articles(
    status: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取全部文章列表，可按 status 筛选（0待审核 1已上线 2已驳回 3已下架）"""
    err = _require_admin(current_user)
    if err:
        return err
    rows, total = await get_admin_articles(db, status, page, page_size)
    return success({
        "list": [{
            "id": a.id,
            "title": a.title,
            "category": a.category,
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


@router.get("/{article_id}/detail")
async def article_detail(
    article_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员预览单条文章完整内容。
    不过滤 status（待审核/已驳回/已下架均可查），且不触发 view_count +1。
    """
    err = _require_admin(current_user)
    if err:
        return err
    article = await get_article_by_id(db, article_id)
    if not article:
        return json_fail("文章不存在", 404)
    author = await get_user_by_id(db, article.author_id)
    return success({
        "id": article.id,
        "title": article.title,
        "category": article.category,
        "cover_img": article.cover_img,
        "content": article.content,
        "summary": article.summary,
        "view_count": article.view_count,
        "status": article.status,
        "reject_reason": article.reject_reason,
        "author_name": author.nickname if author else "",
        "created_at": article.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })


@router.put("/{article_id}/review")
async def review(
    article_id: int,
    form: ArticleReview,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """审核文章：status=1 通过，status=2 驳回（驳回需填 reject_reason）"""
    err = _require_admin(current_user)
    if err:
        return err
    if form.status not in (1, 2):
        return json_fail("status 只能为 1(通过) 或 2(驳回)", 400)
    if form.status == 2 and not form.reject_reason:
        return json_fail("驳回必须填写原因", 400)

    article = await get_article_by_id(db, article_id)
    if not article:
        return json_fail("文章不存在", 404)
    if article.status != 0:
        return json_fail("只能审核待审核状态的文章", 400)

    await review_article(db, article, form.status, form.reject_reason, current_user["user_id"])
    msg = "已通过" if form.status == 1 else "已驳回"
    return success(None, msg)


@router.put("/{article_id}/offline")
async def offline(
    article_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下架已上线的文章"""
    err = _require_admin(current_user)
    if err:
        return err
    article = await get_article_by_id(db, article_id)
    if not article:
        return json_fail("文章不存在", 404)
    if article.status != 1:
        return json_fail("只能下架已上线的文章", 400)
    await offline_article(db, article)
    return success(None, "已下架")
