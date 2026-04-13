# CRUD/diet_article.py
# 饮食文章数据库操作，路由层调用这里，不直接写 SQL
# 函数职责：
#   get_articles          → 用户端列表查询（分类筛选+关键词+分页）
#   get_article_by_id     → 按 ID 查单条
#   increment_view        → 浏览数原子 +1
#   create_article        → 教练新建文章
#   get_coach_articles    → 教练查自己的投稿
#   update_article        → 修改被驳回文章并重置为待审核
#   soft_delete_article   → 软删除
#   get_admin_articles    → 管理员查全部文章（含作者昵称 JOIN）
#   review_article        → 管理员审核（写入审核人/时间）
#   offline_article       → 管理员下架已上线文章

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from models.diet import DietArticle
from models.user import User


async def get_articles(db: AsyncSession, category=None, keyword=None, page=1, page_size=12):
    """用户端：获取已上线文章列表，支持分类筛选和关键词搜索"""
    where = [DietArticle.status == 1, DietArticle.is_deleted == 0]
    if category:
        where.append(DietArticle.category == category)
    if keyword:
        where.append(DietArticle.title.contains(keyword))

    total = (await db.execute(select(func.count(DietArticle.id)).where(*where))).scalar()

    result = await db.execute(
        select(DietArticle).where(*where)
        .order_by(DietArticle.view_count.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def get_article_by_id(db: AsyncSession, article_id: int):
    """按 ID 查文章（含软删除过滤）"""
    result = await db.execute(
        select(DietArticle).where(DietArticle.id == article_id, DietArticle.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def increment_view(db: AsyncSession, article_id: int):
    """浏览数原子 +1"""
    await db.execute(
        update(DietArticle).where(DietArticle.id == article_id)
        .values(view_count=DietArticle.view_count + 1)
    )
    await db.commit()


async def create_article(db: AsyncSession, author_id: int, data: dict):
    """教练创建文章，初始状态为待审核"""
    article = DietArticle(author_id=author_id, **data)
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


async def get_coach_articles(db: AsyncSession, author_id: int):
    """教练查自己投稿的全部文章"""
    result = await db.execute(
        select(DietArticle)
        .where(DietArticle.author_id == author_id, DietArticle.is_deleted == 0)
        .order_by(DietArticle.created_at.desc())
    )
    return result.scalars().all()


async def update_article(db: AsyncSession, article: DietArticle, fields: dict):
    """更新被驳回的文章，重置为待审核"""
    for k, v in fields.items():
        if v is not None:
            setattr(article, k, v)
    article.status = 0
    article.reject_reason = ""
    await db.commit()


async def soft_delete_article(db: AsyncSession, article: DietArticle):
    """软删除"""
    article.is_deleted = 1
    await db.commit()


async def get_admin_articles(db: AsyncSession, status=None, page=1, page_size=20):
    """管理员查文章列表，含投稿教练昵称"""
    where = [DietArticle.is_deleted == 0]
    if status is not None:
        where.append(DietArticle.status == status)

    total = (await db.execute(select(func.count(DietArticle.id)).where(*where))).scalar()

    result = await db.execute(
        select(DietArticle, User.nickname)
        .join(User, DietArticle.author_id == User.id)
        .where(*where)
        .order_by(DietArticle.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return result.all(), total


async def review_article(db: AsyncSession, article: DietArticle, status: int,
                         reject_reason: str, admin_id: int):
    """审核文章：通过(1) 或 驳回(2)"""
    article.status = status
    article.reject_reason = reject_reason or ""
    article.reviewed_by = admin_id
    article.reviewed_at = datetime.now()
    await db.commit()


async def offline_article(db: AsyncSession, article: DietArticle):
    """下架已上线文章"""
    article.status = 3
    await db.commit()
