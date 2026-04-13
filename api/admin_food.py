# api/admin_food.py
# 管理员端食物库审核接口（需管理员登录）
# GET  /admin/foods              查看教练投稿列表（?status=0/1/2）
# PUT  /admin/foods/{id}/approve 通过（食物归入系统库）
# PUT  /admin/foods/{id}/reject  驳回（附原因）

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.diet_record import FoodReview
from CRUD.diet_record import get_admin_foods, review_food
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(tags=["admin-food"])

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
        "created_by": f.created_by,
        "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
    }


@router.get("/admin/foods")
async def list_foods(
    status: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看教练投稿的食物列表，status 不传则返回全部"""
    foods = await get_admin_foods(db, status)
    return success([_food_dict(f) for f in foods])


@router.put("/admin/foods/{food_id}/approve")
async def approve_food(
    food_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通过审核，食物归入系统库（is_custom→0，status→1）"""
    food = await review_food(db, food_id, approve=True)
    if not food:
        return json_fail("食物不存在", 404)
    return success(_food_dict(food), "已通过")


@router.put("/admin/foods/{food_id}/reject")
async def reject_food(
    food_id: int,
    form: FoodReview,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """驳回审核，需填写原因"""
    if not form.reject_reason or not form.reject_reason.strip():
        return json_fail("请填写驳回原因", 400)
    food = await review_food(db, food_id, approve=False, reject_reason=form.reject_reason.strip())
    if not food:
        return json_fail("食物不存在", 404)
    return success(_food_dict(food), "已驳回")
