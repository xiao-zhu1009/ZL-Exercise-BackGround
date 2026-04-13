# api/diet_article.py
# 用户端饮食文章接口（无需登录）
# GET /diet/articles        → 已上线文章列表，支持 category/keyword 筛选和分页
# GET /diet/articles/{id}   → 文章详情，同时触发浏览数 +1

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from CRUD.diet_article import get_articles, get_article_by_id, increment_view
from CRUD.user import get_user_by_id
from utils.response import success, json_fail

router = APIRouter(prefix="/diet/articles", tags=["diet-articles"])


@router.get("")
async def list_articles(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """获取已上线饮食文章列表，支持分类筛选、关键词搜索和分页"""
    articles, total = await get_articles(db, category, keyword, page, page_size)
    return success({
        "list": [{
            "id": a.id,
            "title": a.title,
            "category": a.category,
            "cover_img": a.cover_img,
            "summary": a.summary,
            "view_count": a.view_count,
        } for a in articles],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{article_id}")
async def article_detail(article_id: int, db: AsyncSession = Depends(get_db)):
    """获取文章详情，浏览数 +1"""
    article = await get_article_by_id(db, article_id)
    if not article or article.status != 1:
        return json_fail("文章不存在", 404)

    await increment_view(db, article_id)

    author = await get_user_by_id(db, article.author_id)
    return success({
        "id": article.id,
        "title": article.title,
        "category": article.category,
        "cover_img": article.cover_img,
        "content": article.content,
        "summary": article.summary,
        "view_count": article.view_count + 1,  # 返回 +1 后的值
        "author_name": author.nickname if author else "",
        "created_at": article.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })
