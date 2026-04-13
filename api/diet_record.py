# api/diet_record.py
# 用户端饮食记录接口（需登录）
# GET    /diet/foods/search?keyword=          搜索食物库
# GET    /diet/records/range?start=&end=      查询日期区间每日营养汇总
# GET    /diet/records?date=                  查询某天饮食记录
# POST   /diet/records                        添加一条饮食记录
# DELETE /diet/records/{id}                   删除一条饮食记录

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.diet_record import DietRecordCreate, DietRecordUpdate
from CRUD.diet_record import search_foods, get_records, get_range_summary, create_record, delete_record, update_record
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(tags=["diet-record"])


@router.get("/diet/foods/search")
async def food_search(
    keyword: str = "",
    category: str = "",
    db: AsyncSession = Depends(get_db),
):
    """搜索食物库，无需登录；keyword/category 均为空时返回全部常用食物"""
    foods = await search_foods(db, keyword, category)
    return success([{
        "id": f.id,
        "name": f.name,
        "unit": f.unit,
        "calories": float(f.calories),
        "protein": float(f.protein),
        "carbs": float(f.carbs),
        "fat": float(f.fat),
        "fiber": float(f.fiber),
        "category": f.category,
    } for f in foods])


# 注意：/diet/records/range 必须在 /diet/records/{record_id} 之前注册
@router.get("/diet/records/range")
async def range_summary(
    start: Optional[str] = None,
    end: Optional[str] = None,
    days: int = 7,          # start/end 均未传时，默认取最近 N 天
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询日期区间内每天的营养素汇总，用于趋势图展示"""
    try:
        end_date   = date.fromisoformat(end)   if end   else date.today()
        start_date = date.fromisoformat(start) if start else end_date - timedelta(days=days - 1)
    except ValueError:
        return json_fail("日期格式错误，请使用 yyyy-MM-dd", 400)

    if (end_date - start_date).days > 90:
        return json_fail("查询区间不能超过 90 天", 400)

    rows = await get_range_summary(db, current_user["user_id"], start_date, end_date)
    # 补全区间内没有记录的日期（值为 0），保证前端折线图连续
    data_map = {r.record_date.isoformat(): r for r in rows}
    result = []
    cur = start_date
    while cur <= end_date:
        key = cur.isoformat()
        r = data_map.get(key)
        result.append({
            "date":     key,
            "calories": round(float(r.calories), 1) if r else 0,
            "protein":  round(float(r.protein),  1) if r else 0,
            "carbs":    round(float(r.carbs),    1) if r else 0,
            "fat":      round(float(r.fat),      1) if r else 0,
        })
        cur += timedelta(days=1)
    return success(result)


@router.get("/diet/records")
async def list_records(
    record_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户某天的饮食记录，date 格式 yyyy-MM-dd，默认今天"""
    try:
        d = date.fromisoformat(record_date) if record_date else date.today()
    except ValueError:
        return json_fail("日期格式错误，请使用 yyyy-MM-dd", 400)

    records = await get_records(db, current_user["user_id"], d)
    return success([{
        "id": r.id,
        "food_id": r.food_id,
        "food_name": r.food_name,
        "meal_type": r.meal_type,
        "amount": float(r.amount),
        "unit": r.unit,
        "calories": float(r.calories),
        "protein": float(r.protein),
        "carbs": float(r.carbs),
        "fat": float(r.fat),
        "record_date": r.record_date.isoformat(),
    } for r in records])


@router.post("/diet/records")
async def add_record(
    form: DietRecordCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加一条饮食记录"""
    if not form.food_name.strip():
        return json_fail("食物名称不能为空", 400)
    if form.amount <= 0:
        return json_fail("食用量必须大于 0", 400)

    data = form.model_dump()
    record = await create_record(db, current_user["user_id"], data)
    return success({
        "id": record.id,
        "food_id": record.food_id,
        "food_name": record.food_name,
        "meal_type": record.meal_type,
        "amount": float(record.amount),
        "unit": record.unit,
        "calories": float(record.calories),
        "protein": float(record.protein),
        "carbs": float(record.carbs),
        "fat": float(record.fat),
        "record_date": record.record_date.isoformat(),
    }, "添加成功")


@router.delete("/diet/records/{record_id}")
async def remove_record(
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除一条饮食记录（软删除，仅本人可操作）"""
    ok = await delete_record(db, record_id, current_user["user_id"])
    if not ok:
        return json_fail("记录不存在", 404)
    return success(None, "已删除")


@router.put("/diet/records/{record_id}")
async def edit_record(
    record_id: int,
    form: DietRecordUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改一条饮食记录（食物名、餐次、食用量、各营养素）"""
    record = await update_record(db, record_id, current_user["user_id"], form.model_dump(exclude_unset=True))
    if not record:
        return json_fail("记录不存在", 404)
    return success({
        "id": record.id,
        "food_name": record.food_name,
        "meal_type": record.meal_type,
        "amount": float(record.amount),
        "unit": record.unit,
        "calories": float(record.calories),
        "protein": float(record.protein),
        "carbs": float(record.carbs),
        "fat": float(record.fat),
        "record_date": record.record_date.isoformat(),
    }, "修改成功")
