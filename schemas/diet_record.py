# schemas/diet_record.py
# 饮食记录 + 食物库请求数据校验
# DietRecordCreate：用户添加一条饮食记录
# DietRecordUpdate：用户修改一条饮食记录（字段全部可选）
# FoodCreate：教练投稿新食物
# FoodReview：管理员审核食物（通过/驳回）

from pydantic import BaseModel
from typing import Optional


class DietRecordCreate(BaseModel):
    food_id: Optional[int] = None       # 从食物库选择时传入，手动输入时为 None
    food_name: str                       # 食物名称（冗余存储，防止食物删除后丢失）
    meal_type: int                       # 1=早餐 2=午餐 3=晚餐 4=加餐
    amount: float                        # 食用量（g）
    calories: float = 0                  # 热量（kcal），由前端按比例计算后传入
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    record_date: str                     # yyyy-MM-dd


class DietRecordUpdate(BaseModel):
    food_name: Optional[str] = None
    meal_type: Optional[int] = None      # 1=早餐 2=午餐 3=晚餐 4=加餐
    amount: Optional[float] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None


class FoodCreate(BaseModel):
    name: str
    unit: str = "g"
    calories: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    category: str = ""   # 主食/肉类/蔬菜/水果/乳制品/坚果/豆制品/补剂/其他


class FoodReview(BaseModel):
    reject_reason: Optional[str] = ""   # 驳回时必填
