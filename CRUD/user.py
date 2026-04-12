# CRUD/user.py
# 用户表的增删改查，路由层调用这里，不直接写 SQL

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.user import User


async def get_user_by_account(db: AsyncSession, account: str):
    """按账号或手机号查用户（用于登录）"""
    result = await db.execute(
        select(User).where(or_(User.username == account, User.phone == account))
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int):
    """按 ID 查用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def check_user_exists(db: AsyncSession, username: str, phone: str):
    """检查账号或手机号是否已注册"""
    result = await db.execute(
        select(User).where(or_(User.username == username, User.phone == phone))
    )
    return result.scalar_one_or_none() is not None


async def is_phone_registered(db: AsyncSession, phone: str) -> bool:
    """手机号是否已被占用（注册流程用）"""
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none() is not None


async def create_user(db: AsyncSession, username: str, password: str, phone: str, nickname: str = None):
    """创建新用户"""
    user = User(username=username, password=password, phone=phone, nickname=nickname)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_profile(db: AsyncSession, user: User, **fields):
    """只更新 fields 中出现的键（由路由层用 model_dump(exclude_unset=True) 传入）"""
    if "nickname" in fields and fields["nickname"] is not None:
        user.nickname = fields["nickname"]
    if "phone" in fields and fields["phone"] is not None:
        user.phone = fields["phone"]
    if "signature" in fields and fields["signature"] is not None:
        user.signature = fields["signature"]
    if "avatar" in fields:
        user.avatar = fields["avatar"] or ""
    await db.commit()


async def update_user_password(db: AsyncSession, user: User, new_password: str):
    """更新用户密码"""
    user.password = new_password
    await db.commit()


async def save_user_token(db: AsyncSession, user: User, token: str):
    """登录后将 token 存入用户记录"""
    user.token = token
    await db.commit()


async def ensure_admin_exists(db: AsyncSession) -> None:
    """启动时检查超级管理员是否存在，不存在则自动创建（幂等）"""
    from config.settings import settings
    result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
    if result.scalar_one_or_none():
        return  # 已存在，跳过

    admin = User(
        username=settings.ADMIN_USERNAME,
        password=settings.ADMIN_PASSWORD,
        nickname=settings.ADMIN_NICKNAME,
        phone=settings.ADMIN_PHONE,
        role="admin",
        status=1,
    )
    db.add(admin)
    await db.commit()
    print(f"[init] 管理员账号已创建：{settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
