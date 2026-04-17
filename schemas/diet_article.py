# schemas/diet_article.py
# 饮食文章请求/响应数据校验模型
# ArticleCreate：教练发布新文章
# ArticleUpdate：教练修改被驳回的文章（字段全部可选）
# ArticleReview：管理员审核（通过/驳回）

from pydantic import BaseModel
from typing import Optional


class ArticleCreate(BaseModel):
    title: str
    category: str                        # 饮食/训练/新手/误区/身材管理/健康/工具/计划
    cover_img: str = ""                  # 封面图相对路径，由上传接口返回
    content: str = ""                    # 正文 HTML
    summary: str = ""                    # 摘要，最多 500 字符


class ArticleUpdate(BaseModel):
    # 全部可选，只传需要修改的字段
    title: Optional[str] = None
    category: Optional[str] = None
    cover_img: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class ArticleReview(BaseModel):
    status: int                          # 1=通过  2=驳回
    reject_reason: Optional[str] = ""   # 驳回时必填
