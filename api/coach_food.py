# api/coach_food.py
# 教练端食物库投稿接口（需教练登录）
# POST   /coach/foods          投稿新食物（status=0 待审核）
# GET    /coach/foods          查看自己的投稿列表
# DELETE /coach/foods/{id}     删除待审核或已驳回的投稿

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.diet_record import FoodCreate
from CRUD.diet_record import create_food, get_coach_foods, delete_coach_food
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(tags=["coach-food"])

STATUS_LABEL = {0: "待审核", 1: "已通过", 2: "已驳回"}


def _food_dict(f):
    return {
        "id": f.id,
        "name": f.name,
        "unit": f.unit,
        "calories": float(f.calories),
        "protein": float(f.protein),
        "carbs": float(f.carbs),
        "fat": float(f.fat),
        "fiber": float(f.fiber),
        "category": f.category,
        "status": f.status,
        "status_label": STATUS_LABEL.get(f.status, ""),
        "reject_reason": f.reject_reason,
        "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
    }


@router.post("/coach/foods")
async def submit_food(
    form: FoodCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """教练投稿新食物，提交后进入待审核"""
    if not form.name.strip():
        return json_fail("食物名称不能为空", 400)
    data = form.model_dump()
    data["name"] = data["name"].strip()
    food = await create_food(db, current_user["user_id"], data)
    return success(_food_dict(food), "投稿成功，等待管理员审核")


@router.get("/coach/foods")
async def my_foods(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看自己的全部投稿"""
    foods = await get_coach_foods(db, current_user["user_id"])
    return success([_food_dict(f) for f in foods])


@router.delete("/coach/foods/{food_id}")
async def remove_food(
    food_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除待审核或已驳回的投稿"""
    ok = await delete_coach_food(db, food_id, current_user["user_id"])
    if not ok:
        return json_fail("记录不存在或已通过审核，无法删除", 400)
    return success(None, "已删除")
