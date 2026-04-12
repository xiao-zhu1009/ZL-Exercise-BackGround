# api/coach_action.py
# 教练端动作投稿接口（需 coach 角色）
# POST   /coach/actions/upload/cover → 上传封面图，返回相对路径
# POST   /coach/actions/upload/video → 上传视频，返回相对路径
# POST   /coach/actions              → 发布新动作（status=0 待审核）
# GET    /coach/actions              → 查看我的全部投稿
# PUT    /coach/actions/{id}         → 修改被驳回的动作，重置为待审核
# DELETE /coach/actions/{id}         → 删除待审核或已驳回的动作

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
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

# ── 文件上传配置 ──────────────────────────────────────────────────────────────
# 封面图：存放在 static/action_covers/，通过 /api/static/action_covers/{文件名} 访问
_COVER_DIR = Path("static/action_covers")
_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}   # 允许的 MIME 类型
_COVER_EXT   = {".jpg", ".jpeg", ".png", ".webp"}          # 允许的后缀
_MAX_COVER   = 5 * 1024 * 1024                             # 封面图最大 5MB

# 视频：存放在 static/action_videos/，通过 /api/static/action_videos/{文件名} 访问
_VIDEO_DIR   = Path("static/action_videos")
_VIDEO_TYPES = {"video/mp4", "video/webm"}                 # 允许的 MIME 类型
_VIDEO_EXT   = {".mp4", ".webm"}                           # 允许的后缀
_MAX_VIDEO   = 200 * 1024 * 1024                           # 视频最大 200MB

# 启动时确保目录存在（parents=True 会自动创建 static/ 父目录）
_COVER_DIR.mkdir(parents=True, exist_ok=True)
_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
# ─────────────────────────────────────────────────────────────────────────────


# 角色校验：非 coach 直接返回 403，路由函数首行调用
def _require_coach(current_user: dict):
    if current_user.get("role") != "coach":
        return json_fail("无权限", 403)

# 教练端动作封面上传
@router.post("/upload/cover")
async def upload_cover(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    上传动作封面图。
    流程：校验格式和大小 → 生成唯一文件名 → 写入 static/action_covers/ → 返回相对路径。
    前端拿到 path 后存入 form.cover_img，提交动作时一起带上。
    """
    err = _require_coach(current_user)
    if err:
        return err

    # 校验 MIME 类型（浏览器上传时由 Content-Type 决定）
    if file.content_type not in _COVER_TYPES:
        return json_fail("封面图请上传 JPG、PNG 或 WebP 格式", 400)

    # 从原始文件名取后缀；取不到时按 MIME 推断
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _COVER_EXT:
        ext = ".jpg"

    raw = await file.read()  # 一次性读入内存，封面图较小可接受
    if len(raw) > _MAX_COVER:
        return json_fail("封面图不能超过 5MB", 400)

    # 文件名格式：{coach_id}_{随机hex}.{ext}，避免重名覆盖
    safe_name = f"{current_user['user_id']}_{uuid4().hex}{ext}"
    (_COVER_DIR / safe_name).write_bytes(raw)

    # 返回相对路径（不含 /api/static/ 前缀），前端自行拼接完整 URL
    return success({"path": f"action_covers/{safe_name}"}, "上传成功")

# 教练端动作教学视频上传
@router.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    上传动作教学视频。
    视频文件较大（最大 200MB），使用流式分块读取避免内存溢出。
    流程：校验格式 → 分块写入 static/action_videos/ → 校验总大小 → 返回相对路径。
    """
    err = _require_coach(current_user)
    if err:
        return err

    if file.content_type not in _VIDEO_TYPES:
        return json_fail("视频请上传 MP4 或 WebM 格式", 400)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _VIDEO_EXT:
        ext = ".mp4"

    safe_name = f"{current_user['user_id']}_{uuid4().hex}{ext}"
    dest = _VIDEO_DIR / safe_name

    # 分块写入：每次读 1MB，避免大文件一次性占满内存
    total = 0
    chunk_size = 1024 * 1024  # 1MB per chunk
    with dest.open("wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_VIDEO:
                dest.unlink(missing_ok=True)  # 超限则删除已写入的临时文件
                return json_fail("视频不能超过 200MB", 400)
            f.write(chunk)

    return success({"path": f"action_videos/{safe_name}"}, "上传成功")


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
