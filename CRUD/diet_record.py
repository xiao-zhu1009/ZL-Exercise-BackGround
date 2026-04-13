# CRUD/diet_record.py
# 饮食记录与食物库数据库操作
# search_foods      → 按关键词模糊搜索食物（仅 status=1 已通过的）
# get_records       → 查询用户某天的全部饮食记录
# get_range_summary → 查询用户某日期区间内每天的营养素汇总
# create_record     → 新增一条饮食记录
# delete_record     → 软删除一条记录（仅本人可删）
# update_record     → 修改饮食记录可编辑字段
# create_food       → 教练投稿新食物（status=0 待审核）
# get_coach_foods   → 查询教练自己的投稿列表
# delete_coach_food → 教练删除待审核/驳回的投稿
# get_admin_foods   → 管理员查食物投稿列表（可按 status 筛选）
# review_food       → 管理员通过/驳回食物投稿
# ensure_foods      → 启动时写入系统预置食物（幂等）

from datetime import date as date_type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.diet import Food, DietRecord


async def search_foods(db: AsyncSession, keyword: str, category: str = "", limit: int = 50):
    """模糊搜索食物名称，只返回 status=1（已通过）的食物，系统库优先"""
    q = select(Food).where(Food.is_deleted == 0, Food.status == 1)
    if keyword:
        q = q.where(Food.name.contains(keyword))
    if category:
        q = q.where(Food.category == category)
    q = q.order_by(Food.is_custom.asc(), Food.name.asc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_records(db: AsyncSession, user_id: int, record_date: date_type):
    """查询用户某天的全部饮食记录，按餐次和创建时间排序"""
    result = await db.execute(
        select(DietRecord)
        .where(
            DietRecord.user_id == user_id,
            DietRecord.record_date == record_date,
            DietRecord.is_deleted == 0,
        )
        .order_by(DietRecord.meal_type.asc(), DietRecord.created_at.asc())
    )
    return result.scalars().all()


async def get_range_summary(db: AsyncSession, user_id: int, start: date_type, end: date_type):
    """按日期区间聚合每天的热量/蛋白质/碳水/脂肪总量，返回列表按日期升序"""
    result = await db.execute(
        select(
            DietRecord.record_date,
            func.sum(DietRecord.calories).label("calories"),
            func.sum(DietRecord.protein).label("protein"),
            func.sum(DietRecord.carbs).label("carbs"),
            func.sum(DietRecord.fat).label("fat"),
        )
        .where(
            DietRecord.user_id == user_id,
            DietRecord.record_date >= start,
            DietRecord.record_date <= end,
            DietRecord.is_deleted == 0,
        )
        .group_by(DietRecord.record_date)
        .order_by(DietRecord.record_date.asc())
    )
    return result.all()


async def create_record(db: AsyncSession, user_id: int, data: dict):
    """新增饮食记录"""
    from datetime import date, datetime
    # record_date 由字符串转 date
    if isinstance(data.get("record_date"), str):
        data["record_date"] = date.fromisoformat(data["record_date"])

    record = DietRecord(user_id=user_id, **data)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_record(db: AsyncSession, record_id: int, user_id: int):
    """软删除，返回 True 表示成功，False 表示记录不存在或无权限"""
    result = await db.execute(
        select(DietRecord).where(
            DietRecord.id == record_id,
            DietRecord.user_id == user_id,
            DietRecord.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    record.is_deleted = 1
    await db.commit()
    return True


async def update_record(db: AsyncSession, record_id: int, user_id: int, fields: dict):
    """更新饮食记录的可编辑字段，返回更新后的对象，None 表示不存在或无权限"""
    result = await db.execute(
        select(DietRecord).where(
            DietRecord.id == record_id,
            DietRecord.user_id == user_id,
            DietRecord.is_deleted == 0,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return None
    # 只允许修改这几个字段
    allowed = {"food_name", "meal_type", "amount", "calories", "protein", "carbs", "fat"}
    for k, v in fields.items():
        if k in allowed and v is not None:
            setattr(record, k, v)
    await db.commit()
    await db.refresh(record)
    return record


# ── 食物库管理 ────────────────────────────────────────────────────────────────

async def create_food(db: AsyncSession, coach_id: int, data: dict):
    """教练投稿新食物，status=0 待审核，is_custom=1"""
    food = Food(is_custom=1, status=0, created_by=coach_id, **data)
    db.add(food)
    await db.commit()
    await db.refresh(food)
    return food


async def get_coach_foods(db: AsyncSession, coach_id: int):
    """查询教练自己投稿的全部食物（含各状态）"""
    result = await db.execute(
        select(Food)
        .where(Food.created_by == coach_id, Food.is_custom == 1, Food.is_deleted == 0)
        .order_by(Food.created_at.desc())
    )
    return result.scalars().all()


async def delete_coach_food(db: AsyncSession, food_id: int, coach_id: int):
    """教练删除自己待审核或已驳回的投稿，返回 True 成功"""
    result = await db.execute(
        select(Food).where(
            Food.id == food_id,
            Food.created_by == coach_id,
            Food.is_custom == 1,
            Food.status.in_([0, 2]),   # 只能删待审核/驳回的
            Food.is_deleted == 0,
        )
    )
    food = result.scalar_one_or_none()
    if not food:
        return False
    food.is_deleted = 1
    await db.commit()
    return True


async def get_admin_foods(db: AsyncSession, status=None, limit: int = 100, offset: int = 0):
    """管理员查食物投稿列表，status=None 时返回全部教练投稿"""
    q = select(Food).where(Food.is_custom == 1, Food.is_deleted == 0)
    if status is not None:
        q = q.where(Food.status == status)
    q = q.order_by(Food.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


async def review_food(db: AsyncSession, food_id: int, approve: bool, reject_reason: str = ""):
    """管理员审核：approve=True 通过（is_custom→0），False 驳回"""
    result = await db.execute(
        select(Food).where(Food.id == food_id, Food.is_custom == 1, Food.is_deleted == 0)
    )
    food = result.scalar_one_or_none()
    if not food:
        return None
    if approve:
        food.status = 1
        food.is_custom = 0   # 通过后归入系统库，用户端可搜索
        food.reject_reason = ""
    else:
        food.status = 2
        food.reject_reason = reject_reason
    await db.commit()
    await db.refresh(food)
    return food


# 系统预置食物数据（每 100g 的营养素）
_PRESET_FOODS = [
    ("鸡胸肉", "g", 165, 31.0, 0.0, 3.6, 0.0, "肉类"),
    ("猪里脊", "g", 143, 20.2, 0.0, 7.9, 0.0, "肉类"),
    ("牛腱子", "g", 106, 17.9, 0.0, 4.2, 0.0, "肉类"),
    ("三文鱼", "g", 208, 20.4, 0.0, 13.4, 0.0, "鱼类"),
    ("鸡蛋", "g", 144, 12.7, 1.5, 9.0, 0.0, "蛋类"),
    ("牛奶", "ml", 61, 3.2, 4.8, 3.2, 0.0, "乳制品"),
    ("希腊酸奶", "g", 97, 9.0, 3.6, 5.0, 0.0, "乳制品"),
    ("米饭(熟)", "g", 116, 2.6, 25.6, 0.3, 0.3, "主食"),
    ("燕麦", "g", 389, 16.9, 66.3, 6.9, 10.6, "主食"),
    ("全麦面包", "g", 247, 9.0, 41.3, 3.4, 6.9, "主食"),
    ("红薯", "g", 86, 1.6, 20.1, 0.1, 3.0, "主食"),
    ("西兰花", "g", 34, 2.8, 6.6, 0.4, 2.6, "蔬菜"),
    ("菠菜", "g", 23, 2.9, 3.6, 0.4, 2.2, "蔬菜"),
    ("番茄", "g", 18, 0.9, 3.9, 0.2, 1.2, "蔬菜"),
    ("香蕉", "g", 89, 1.1, 22.8, 0.3, 2.6, "水果"),
    ("苹果", "g", 52, 0.3, 13.8, 0.2, 2.4, "水果"),
    ("蓝莓", "g", 57, 0.7, 14.5, 0.3, 2.4, "水果"),
    ("花生", "g", 567, 25.8, 16.1, 49.2, 8.5, "坚果"),
    ("杏仁", "g", 579, 21.2, 21.6, 49.9, 12.5, "坚果"),
    ("橄榄油", "ml", 884, 0.0, 0.0, 100.0, 0.0, "油脂"),
    ("豆腐", "g", 76, 8.1, 1.9, 4.8, 0.3, "豆制品"),
    ("黑豆", "g", 341, 36.0, 33.6, 15.9, 10.2, "豆制品"),
    ("蛋白粉", "g", 400, 80.0, 10.0, 5.0, 0.0, "补剂"),
]


async def ensure_foods(db: AsyncSession):
    """启动时幂等写入系统预置食物，已存在则跳过"""
    count = (await db.execute(
        select(func.count(Food.id)).where(Food.is_custom == 0, Food.is_deleted == 0)
    )).scalar()
    if count >= len(_PRESET_FOODS):
        return  # 已初始化，跳过

    for name, unit, cal, pro, carb, fat, fiber, cat in _PRESET_FOODS:
        exists = (await db.execute(
            select(Food.id).where(Food.name == name, Food.is_custom == 0)
        )).scalar_one_or_none()
        if not exists:
            db.add(Food(
                name=name, unit=unit, calories=cal, protein=pro,
                carbs=carb, fat=fat, fiber=fiber, category=cat,
                is_custom=0, status=1  # 系统预置直接通过
            ))
    await db.commit()
