# api/admin_statistics.py
# 管理员数据统计接口：汇总各业务表真实数量及用户注册趋势（支持按月/日粒度）

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.session import get_db
from models.user import User
from models.action import Action
from models.diet import DietArticle
from models.course import Course, Reservation
from utils.deps import get_current_user
from utils.response import success

router = APIRouter(prefix="/admin", tags=["admin-statistics"])


def _require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权限")
    return current_user


@router.get("/statistics")
async def get_statistics(
    granularity: str = Query("month", regex="^(month|day)$"),  # month=近6个月 day=近30天
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(_require_admin)
):
    """汇总各业务表数量及用户注册趋势，granularity=month 按月/day 按日"""

    # 总用户数（未删除）
    total_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_deleted == 0)
    )).scalar()

    # 活跃用户：状态正常（未封禁）且未删除
    active_users = (await db.execute(
        select(func.count()).select_from(User).where(User.status == 1, User.is_deleted == 0)
    )).scalar()

    # 已上线动作数
    total_actions = (await db.execute(
        select(func.count()).select_from(Action).where(Action.status == 1, Action.is_deleted == 0)
    )).scalar()

    # 已上线文章数
    total_articles = (await db.execute(
        select(func.count()).select_from(DietArticle).where(DietArticle.status == 1, DietArticle.is_deleted == 0)
    )).scalar()

    # 有效课程数：招募中(1)/满员(2)/已结束(3) 均算已上线
    total_courses = (await db.execute(
        select(func.count()).select_from(Course).where(Course.status.in_([1, 2, 3]), Course.is_deleted == 0)
    )).scalar()

    # 预约总数（未删除）
    total_reservations = (await db.execute(
        select(func.count()).select_from(Reservation).where(Reservation.is_deleted == 0)
    )).scalar()

    user_growth = await _query_growth(db, granularity)

    return success({
        "total_users": total_users,
        "active_users": active_users,
        "total_actions": total_actions,
        "total_articles": total_articles,
        "total_courses": total_courses,
        "total_reservations": total_reservations,
        "user_growth": user_growth
    })


async def _query_growth(db: AsyncSession, granularity: str) -> list:
    """按月或按日统计用户注册趋势，无数据的时间点补0"""
    now = datetime.now()

    if granularity == "month":
        # 近6个月，格式 "%Y-%m"
        start = _subtract_months(datetime(now.year, now.month, 1), 5)
        fmt = "%Y-%m"
        rows = (await db.execute(
            select(func.date_format(User.created_at, fmt).label("key"), func.count().label("cnt"))
            .where(User.created_at >= start, User.is_deleted == 0)
            .group_by("key").order_by("key")
        )).all()
        row_map = {r.key: r.cnt for r in rows}

        # 生成近6个月完整列表，补齐空月
        slots = []
        for i in range(5, -1, -1):
            d = _subtract_months(datetime(now.year, now.month, 1), i)
            key = d.strftime(fmt)
            label = f"{d.month}月"
            slots.append({"label": label, "count": row_map.get(key, 0)})

    else:
        # 近30天，格式 "%m-%d"
        start = datetime(now.year, now.month, now.day) - timedelta(days=29)
        fmt = "%Y-%m-%d"  # 查询用完整日期避免跨年重复
        rows = (await db.execute(
            select(func.date_format(User.created_at, fmt).label("key"), func.count().label("cnt"))
            .where(User.created_at >= start, User.is_deleted == 0)
            .group_by("key").order_by("key")
        )).all()
        row_map = {r.key: r.cnt for r in rows}

        # 生成近30天完整列表，补齐空日
        slots = []
        for i in range(29, -1, -1):
            d = start + timedelta(days=i)
            key = d.strftime(fmt)
            label = d.strftime("%m-%d")
            slots.append({"label": label, "count": row_map.get(key, 0)})

    return slots


def _subtract_months(dt: datetime, months: int) -> datetime:
    """将 datetime 往前推 months 个月，返回该月1日"""
    month = dt.month - months
    year = dt.year
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1)
