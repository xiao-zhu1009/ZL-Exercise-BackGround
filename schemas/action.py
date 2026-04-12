# schemas/action.py
# 动作库请求/响应数据校验模型
# ActionCreate：教练发布新动作
# ActionUpdate：教练修改被驳回的动作（字段全部可选）
# ActionReview：管理员审核（通过/驳回）

from pydantic import BaseModel
from typing import List, Optional


class ActionCreate(BaseModel):
    title: str
    body_part: str                       # 胸/背/腿/肩/手臂/核心
    category: str                        # 力量/有氧/拉伸/综合
    difficulty: int = 1                  # 1初级 2中级 3高级
    cover_img: str = ""                  # 封面图相对路径
    video_url: str = ""                  # 视频相对路径
    description: Optional[str] = None
    steps: Optional[List[str]] = None   # 步骤列表
    cautions: Optional[List[str]] = None  # 注意事项列表


class ActionUpdate(BaseModel):
    # 全部可选，只传需要修改的字段
    title: Optional[str] = None
    body_part: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[int] = None
    cover_img: Optional[str] = None
    video_url: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[str]] = None
    cautions: Optional[List[str]] = None


class ActionReview(BaseModel):
    status: int                          # 1=通过  2=驳回
    reject_reason: Optional[str] = ""   # 驳回时必填
