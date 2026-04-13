# CRUD/coach_profile.py
# 教练主页数据层：获取/创建/更新 coach_profiles，聚合 users + user_body_stats

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.coach_profile import CoachProfile
from models.user import User
from models.body_stats import UserBodyStats


async def get_coach_profile(db: AsyncSession, user_id: int) -> CoachProfile | None:
    """按 user_id 查教练扩展信息，不存在返回 None"""
    result = await db.execute(
        select(CoachProfile).where(CoachProfile.user_id == user_id, CoachProfile.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def get_or_create_coach_profile(db: AsyncSession, user_id: int) -> CoachProfile:
    """获取教练扩展信息，不存在则自动创建空记录（幂等）"""
    profile = await get_coach_profile(db, user_id)
    if not profile:
        profile = CoachProfile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update_coach_profile(db: AsyncSession, profile: CoachProfile, data: dict) -> CoachProfile:
    """更新教练扩展字段，只更新 data 中出现的键"""
    fields = [
        "real_name", "gender", "age", "years_exp",
        "specialties", "certifications", "intro", "location", "is_accepting"
    ]
    for f in fields:
        if f in data and data[f] is not None:
            setattr(profile, f, data[f])
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_full_coach_info(db: AsyncSession, user_id: int) -> dict | None:
    """聚合 users + user_body_stats + coach_profiles，返回教练完整信息"""
    user_result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == 0)
    )
    user = user_result.scalar_one_or_none()
    if not user or user.role != "coach":
        return None

    stats_result = await db.execute(
        select(UserBodyStats).where(UserBodyStats.user_id == user_id)
    )
    stats = stats_result.scalar_one_or_none()

    profile = await get_coach_profile(db, user_id)

    return _build_coach_dict(user, stats, profile, public=False)


async def get_public_coach_info(db: AsyncSession, user_id: int) -> dict | None:
    """用户端查看教练公开信息（脱敏：不返回手机号）"""
    user_result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == 0, User.status == 1)
    )
    user = user_result.scalar_one_or_none()
    if not user or user.role != "coach":
        return None

    stats_result = await db.execute(
        select(UserBodyStats).where(UserBodyStats.user_id == user_id)
    )
    stats = stats_result.scalar_one_or_none()
    profile = await get_coach_profile(db, user_id)

    return _build_coach_dict(user, stats, profile, public=True)


def _build_coach_dict(user: User, stats: UserBodyStats | None, profile: CoachProfile | None, public: bool) -> dict:
    """组装教练信息字典；public=True 时隐藏手机号和真实姓名"""
    data = {
        "id":        user.id,
        "username":  user.username,
        "nickname":  user.nickname or user.username,
        "avatar":    user.avatar,
        "signature": user.signature,
        "goal":      user.goal,
        # 身体指标
        "height":    float(stats.height) if stats and stats.height else None,
        "weight":    float(stats.weight) if stats and stats.weight else None,
        "bmi":       round(float(stats.bmi), 1) if stats and stats.bmi else None,
        "body_fat":  float(stats.body_fat) if stats and stats.body_fat else None,
        # 教练专属
        "gender":         profile.gender if profile else 0,
        "age":            profile.age if profile else None,
        "years_exp":      profile.years_exp if profile else 0,
        "specialties":    profile.specialties if profile else "",
        "certifications": profile.certifications if profile else "",
        "intro":          profile.intro if profile else "",
        "location":       profile.location if profile else "",
        "is_accepting":   profile.is_accepting if profile else 1,
    }
    if not public:
        # 教练自己查看时返回手机号和真实姓名
        data["phone"] = user.phone
        data["real_name"] = profile.real_name if profile else ""
    return data
