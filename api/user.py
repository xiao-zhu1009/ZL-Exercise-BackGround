# api/user.py
# 用户路由：个人信息、身体指标、修改密码、头像上传

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.user import ProfileUpdate, BodyStatsUpdate, PasswordUpdate
from utils.deps import get_current_user
from utils.response import success, json_fail
from CRUD.user import get_user_by_id, update_user_profile, update_user_password
from CRUD.body_stats import get_body_stats, upsert_body_stats

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取个人信息"""
    user = await get_user_by_id(db, current_user["user_id"])
    if not user:
        return json_fail("用户不存在", 404)
    return success({
        "username": user.username,
        "nickname": user.nickname,
        "phone": user.phone,
        "signature": user.signature,
        "avatar": user.avatar
    })


@router.put("/profile")
async def update_profile(form: ProfileUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """修改个人信息（body 里带 avatar: \"\" 可恢复默认头像）"""
    user = await get_user_by_id(db, current_user["user_id"])
    data = form.model_dump(exclude_unset=True)
    await update_user_profile(db, user, **data)
    return success(None, "保存成功")


_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_MAX_AVATAR_BYTES = 2 * 1024 * 1024


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传自定义头像，返回可访问 URL 并写入 users.avatar"""
    if file.content_type not in _AVATAR_TYPES:
        return json_fail("请上传 JPG、PNG、GIF 或 WebP 图片", 400)
    user = await get_user_by_id(db, current_user["user_id"])
    if not user:
        return json_fail("用户不存在", 404)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _AVATAR_EXT:
        ext = ".jpg" if file.content_type == "image/jpeg" else ".png"

    raw = await file.read()
    if len(raw) > _MAX_AVATAR_BYTES:
        return json_fail("图片不能超过 2MB", 400)

    upload_dir = Path("static/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{user.id}_{uuid4().hex}{ext}"
    dest = upload_dir / safe_name
    dest.write_bytes(raw)

    base = str(request.base_url).rstrip("/")
    url = f"{base}/api/static/avatars/{safe_name}"
    await update_user_profile(db, user, avatar=url)
    return success({"avatar": url}, "头像已更新")


@router.get("/body-stats")
async def get_body_stats_api(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取身体指标"""
    stats = await get_body_stats(db, current_user["user_id"])
    if not stats:
        return success(None)
    return success({
        "height": stats.height,
        "weight": stats.weight,
        "bmi": round(stats.bmi, 1) if stats.bmi else None,
        "body_fat": stats.body_fat,
        "waist": stats.waist,
        "hip": stats.hip,
        "whr": round(stats.whr, 2) if stats.whr else None
    })


@router.put("/body-stats")
async def update_body_stats(form: BodyStatsUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """修改身体指标，自动计算 BMI 和 WHR"""
    stats = await upsert_body_stats(db, current_user["user_id"], form)
    return success({
        "bmi": round(stats.bmi, 1) if stats.bmi else None,
        "whr": round(stats.whr, 2) if stats.whr else None
    }, "保存成功")


@router.put("/password")
async def update_password(form: PasswordUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """修改密码"""
    if form.old_password == form.new_password:
        return json_fail("新密码不能与旧密码相同", 400)
    user = await get_user_by_id(db, current_user["user_id"])
    if user.password != form.old_password:
        return json_fail("旧密码错误", 400)
    await update_user_password(db, user, form.new_password)
    return success(None, "密码修改成功")
