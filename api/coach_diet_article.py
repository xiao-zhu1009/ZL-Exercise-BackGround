# api/coach_diet_article.py
# 教练端饮食文章投稿接口（需 coach 角色）
# POST   /coach/diet/articles/upload/cover → 上传封面图，返回相对路径
# POST   /coach/diet/articles              → 发布新文章（status=0 待审核）
# GET    /coach/diet/articles              → 查看我的全部投稿
# PUT    /coach/diet/articles/{id}         → 修改被驳回的文章，重置为待审核
# DELETE /coach/diet/articles/{id}         → 删除待审核或已驳回的文章

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.diet_article import ArticleCreate, ArticleUpdate
from CRUD.diet_article import (
    create_article, get_coach_articles,
    get_article_by_id, update_article, soft_delete_article,
)
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/coach/diet/articles", tags=["coach-diet-articles"])

# ── 封面图上传配置 ─────────────────────────────────────────────────────────────
_COVER_DIR   = Path("static/diet_covers")
_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
_COVER_EXT   = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_COVER   = 5 * 1024 * 1024   # 5MB

_COVER_DIR.mkdir(parents=True, exist_ok=True)
# ─────────────────────────────────────────────────────────────────────────────


def _require_coach(current_user: dict):
    """非 coach 角色直接返回 403"""
    if current_user.get("role") != "coach":
        return json_fail("无权限", 403)


@router.post("/upload/cover")
async def upload_cover(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    上传文章封面图。
    流程：校验格式和大小 → 生成唯一文件名 → 写入 static/diet_covers/ → 返回相对路径。
    前端拿到 path 后存入 form.cover_img，发布文章时一起带上。
    """
    err = _require_coach(current_user)
    if err:
        return err

    if file.content_type not in _COVER_TYPES:
        return json_fail("封面图请上传 JPG、PNG 或 WebP 格式", 400)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _COVER_EXT:
        ext = ".jpg"

    raw = await file.read()
    if len(raw) > _MAX_COVER:
        return json_fail("封面图不能超过 5MB", 400)

    safe_name = f"{current_user['user_id']}_{uuid4().hex}{ext}"
    (_COVER_DIR / safe_name).write_bytes(raw)

    return success({"path": f"diet_covers/{safe_name}"}, "上传成功")

# 教练端文章投稿提交审核接口
@router.post("")
async def publish_article(
    form: ArticleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布新文章，初始状态为待审核"""
    err = _require_coach(current_user)
    if err:
        return err
    article = await create_article(db, current_user["user_id"], form.model_dump())
    return success({"id": article.id}, "提交成功，等待审核")

# 教练端获取已提交的文章信息接口
@router.get("")
async def my_articles(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我投稿的全部文章"""
    err = _require_coach(current_user)
    if err:
        return err
    articles = await get_coach_articles(db, current_user["user_id"])
    return success([{
        "id": a.id,
        "title": a.title,
        "category": a.category,
        "cover_img": a.cover_img or "",
        "summary": a.summary or "",
        "content": a.content or "",   # 修改回显需要完整正文
        "status": a.status,
        "reject_reason": a.reject_reason,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for a in articles])


@router.put("/{article_id}")
async def edit_article(
    article_id: int,
    form: ArticleUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改被驳回的文章并重新提交审核"""
    err = _require_coach(current_user)
    if err:
        return err
    article = await get_article_by_id(db, article_id)
    if not article or article.author_id != current_user["user_id"]:
        return json_fail("文章不存在", 404)
    if article.status != 2:
        return json_fail("只能修改已驳回的文章", 400)
    await update_article(db, article, form.model_dump(exclude_unset=True))
    return success(None, "已重新提交审核")

# 教练端删除已提交待审核/已驳回的文章接口
@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除待审核或已驳回的文章"""
    err = _require_coach(current_user)
    if err:
        return err
    article = await get_article_by_id(db, article_id)
    if not article or article.author_id != current_user["user_id"]:
        return json_fail("文章不存在", 404)
    if article.status not in (0, 2):
        return json_fail("只能删除待审核或已驳回的文章", 400)
    await soft_delete_article(db, article)
    return success(None, "已删除")
