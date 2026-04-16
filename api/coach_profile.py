# api/coach_profile.py
# 教练主页接口
# GET  /coach/profile          教练查看自己的完整主页
# PUT  /coach/profile          教练修改主页信息（含身体指标）
# PUT  /coach/profile/password 教练修改密码
# POST /coach/profile/avatar   教练上传头像
# GET  /coaches/{id}           用户端查看教练公开主页（已有 /coaches 列表，这里补详情）

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from utils.deps import get_current_user
from utils.response import success, json_fail
from schemas.coach_profile import CoachProfileUpdate
from schemas.user import PasswordUpdate
from CRUD.coach_profile import (
    get_or_create_coach_profile, update_coach_profile,
    get_full_coach_info, get_public_coach_info,
)
from CRUD.user import get_user_by_id, update_user_profile, update_user_password
from CRUD.body_stats import upsert_body_stats_from_partial

router = APIRouter(tags=["coach-profile"])

_IMG_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_IMG_EXT   = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_MAX_BYTES = 2 * 1024 * 1024


def _require_coach(current_user: dict):
    if current_user["role"] != "coach":
        return json_fail("无权限，仅教练可操作", 403)
    return None


# ── 教练端 ────────────────────────────────────────────────
# 获取教练端基本信息
@router.get("/coach/profile")
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练查看自己的完整主页（含手机号、真实姓名）"""
    err = _require_coach(current_user)
    if err:
        return err

    info = await get_full_coach_info(db, current_user["user_id"])
    if not info:
        return json_fail("用户不存在", 404)
    return success(info)

# 修改教练端基本信息
@router.put("/coach/profile")
async def update_my_profile(
    form: CoachProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练修改主页信息（users + coach_profiles + user_body_stats 分表更新）"""
    err = _require_coach(current_user)
    if err:
        return err

    user = await get_user_by_id(db, current_user["user_id"])
    if not user:
        return json_fail("用户不存在", 404)

    # 更新 users 表字段
    user_fields = form.model_dump(include={"nickname", "phone", "signature", "goal"}, exclude_unset=True)
    if user_fields:
        await update_user_profile(db, user, **user_fields)

    # 更新 coach_profiles 表字段
    profile_fields = form.model_dump(
        include={"real_name", "gender", "age", "years_exp", "specialties",
                 "certifications", "intro", "location", "is_accepting"},
        exclude_unset=True,
    )
    if profile_fields:
        profile = await get_or_create_coach_profile(db, user.id)
        await update_coach_profile(db, profile, profile_fields)

    stats_fields = form.model_dump(
        include={"height", "weight", "body_fat", "waist", "hip"},
        exclude_unset=True,
    )
    # 更新user_body_stats表字段
    if stats_fields:
        await upsert_body_stats_from_partial(db, user.id, stats_fields)

    return success(None, "保存成功")


@router.put("/coach/profile/password")
async def change_password(
    form: PasswordUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练修改密码"""
    err = _require_coach(current_user)
    if err:
        return err

    if form.old_password == form.new_password:
        return json_fail("新密码不能与旧密码相同", 400)

    user = await get_user_by_id(db, current_user["user_id"])
    if user.password != form.old_password:
        return json_fail("旧密码错误", 400)

    await update_user_password(db, user, form.new_password)
    return success(None, "密码修改成功")


@router.post("/coach/profile/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练上传头像"""
    err = _require_coach(current_user)
    if err:
        return err

    if file.content_type not in _IMG_TYPES:
        return json_fail("请上传 JPG、PNG、GIF 或 WebP 图片", 400)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _IMG_EXT:
        ext = ".jpg" if file.content_type == "image/jpeg" else ".png"

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        return json_fail("图片不能超过 2MB", 400)

    upload_dir = Path("static/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{current_user['user_id']}_{uuid4().hex}{ext}"
    (upload_dir / safe_name).write_bytes(raw)

    base = str(request.base_url).rstrip("/")
    url = f"{base}/api/static/avatars/{safe_name}"

    user = await get_user_by_id(db, current_user["user_id"])
    await update_user_profile(db, user, avatar=url)
    return success({"avatar": url}, "头像已更新")


# ── 用户端：查看教练公开主页 ──────────────────────────────
# 用户端获取教练基本信息接口
@router.get("/coaches/{coach_id}")
async def get_coach_public_profile(
    coach_id: int,
    db: AsyncSession = Depends(get_db),
):
    """用户端查看教练公开主页（脱敏：不返回手机号和真实姓名）"""
    info = await get_public_coach_info(db, coach_id)
    if not info:
        return json_fail("教练不存在", 404)
    return success(info)
