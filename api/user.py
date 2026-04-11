# api/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models.user import User
from models.body_stats import UserBodyStats
from schemas.user import ProfileUpdate, BodyStatsUpdate, PasswordUpdate
from utils.deps import get_current_user
from utils.response import success

router = APIRouter(prefix="/user", tags=["user"])

# 个人主页基本信息获取
@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return success({
        "username": user.username,
        "nickname": user.nickname,
        "phone": user.phone,
        "signature": user.signature,
        "avatar": user.avatar
    })
# 修改个人主页基本信息
@router.put("/profile")
async def update_profile(form: ProfileUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one()
    if form.nickname is not None:
        user.nickname = form.nickname
    if form.phone is not None:
        user.phone = form.phone
    if form.signature is not None:
        user.signature = form.signature
    await db.commit()
    return success(None, "保存成功")

# 用户身体指标获取
@router.get("/body-stats")
async def get_body_stats(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserBodyStats).where(UserBodyStats.user_id == current_user["user_id"]))
    stats = result.scalar_one_or_none()
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

# 用户身体指标修改
@router.put("/body-stats")
async def update_body_stats(form: BodyStatsUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserBodyStats).where(UserBodyStats.user_id == current_user["user_id"]))
    stats = result.scalar_one_or_none()
    if not stats:
        stats = UserBodyStats(user_id=current_user["user_id"])
        db.add(stats)

    for field in ("height", "weight", "body_fat", "waist", "hip"):
        val = getattr(form, field)
        if val is not None:
            setattr(stats, field, val)

    # 自动计算 bmi 和 whr
    if stats.height and stats.weight:
        stats.bmi = stats.weight / ((stats.height / 100) ** 2)
    if stats.waist and stats.hip:
        stats.whr = stats.waist / stats.hip

    await db.commit()
    return success({
        "bmi": round(stats.bmi, 1) if stats.bmi else None,
        "whr": round(stats.whr, 2) if stats.whr else None
    }, "保存成功")


@router.put("/password")
async def update_password(form: PasswordUpdate, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if form.old_password == form.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one()
    if user.password != form.old_password:
        raise HTTPException(status_code=400, detail="旧密码错误")
    user.password = form.new_password
    await db.commit()
    return success(None, "密码修改成功")
