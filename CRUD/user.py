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


async def update_user_profile(db: AsyncSession, user: User, nickname: str = None, phone: str = None, signature: str = None):
    """更新用户基本信息（只更新传入的字段）"""
    if nickname is not None:
        user.nickname = nickname
    if phone is not None:
        user.phone = phone
    if signature is not None:
        user.signature = signature
    await db.commit()


async def update_user_password(db: AsyncSession, user: User, new_password: str):
    """更新用户密码"""
    user.password = new_password
    await db.commit()


async def save_user_token(db: AsyncSession, user: User, token: str):
    """登录后将 token 存入用户记录"""
    user.token = token
    await db.commit()
