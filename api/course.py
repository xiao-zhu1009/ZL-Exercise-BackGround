# api/course.py
# 用户端课程接口（列表/详情无需登录，预约相关需登录）
# GET    /courses                      课程列表（招募中+满员，筛选+分页）
# GET    /courses/{id}                 课程详情
# POST   /courses/{id}/reserve         申请预约
# GET    /courses/my-reservations      我的预约列表
# DELETE /courses/reservations/{id}    取消预约

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from CRUD.course import (
    get_courses, get_course_by_id, get_reservation,
    create_reservation, get_user_reservations, cancel_reservation,
    get_reservation_by_id,
)
from CRUD.user import get_user_by_id
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/courses", tags=["courses"])

# 课程状态文案
_STATUS_LABEL = {0: "待审核", 1: "招募中", 2: "满员", 3: "已结束", 4: "已驳回", 5: "已下架"}


def _fmt_course(c, coach_name=""):
    return {
        "id": c.id,
        "title": c.title,
        "category": c.category,
        "difficulty": c.difficulty,
        "cover_img": c.cover_img,
        "price": str(c.price),
        "max_people": c.max_people,
        "enrolled": c.enrolled,
        "start_time": c.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": c.end_time.strftime("%Y-%m-%d %H:%M:%S") if c.end_time else "",
        "location": c.location,
        "status": c.status,
        "coach_name": coach_name,
    }


@router.get("/my-reservations")
async def my_reservations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的全部预约记录"""
    rows = await get_user_reservations(db, current_user["user_id"])
    return success([{
        "reservation_id": r.id,
        "course_id": r.course_id,
        "course_title": title,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "location": location,
        "coach_name": coach_name or "",
        "status": r.status,
        "cancel_reason": r.cancel_reason,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for r, title, start_time, location, coach_name in rows])


@router.get("")
async def list_courses(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """获取招募中和满员的课程列表，支持分类筛选和关键词搜索"""
    courses, total = await get_courses(db, category, keyword, page, page_size)
    result = []
    for c in courses:
        coach = await get_user_by_id(db, c.coach_id)
        result.append({
            "id": c.id,
            "title": c.title,
            "category": c.category,
            "difficulty": c.difficulty,
            "cover_img": c.cover_img,
            "price": str(c.price),
            "max_people": c.max_people,
            "enrolled": c.enrolled,
            "start_time": c.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "location": c.location,
            "status": c.status,
            "coach_name": coach.nickname if coach else "",
        })
    return success({"list": result, "total": total, "page": page, "page_size": page_size})


@router.get("/{course_id}")
async def course_detail(course_id: int, db: AsyncSession = Depends(get_db)):
    """获取课程详情（招募中/满员均可查）"""
    course = await get_course_by_id(db, course_id)
    if not course or course.status not in (1, 2):
        return json_fail("课程不存在", 404)
    coach = await get_user_by_id(db, course.coach_id)
    data = _fmt_course(course, coach.nickname if coach else "")
    data["description"] = course.description or ""
    return success(data)


@router.post("/{course_id}/reserve")
async def reserve_course(
    course_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """申请预约课程，初始状态为待审批"""
    course = await get_course_by_id(db, course_id)
    if not course or course.status != 1:
        return json_fail("课程不存在或不在招募中", 400)
    if course.enrolled >= course.max_people:
        return json_fail("课程已满员", 400)

    existing = await get_reservation(db, current_user["user_id"], course_id)
    if existing:
        # 待审批(1) 或 已确认(2)：不允许重复申请
        if existing.status in (1, 2):
            return json_fail("已有预约记录，请勿重复申请", 400)
        # 已取消(0) 或 已拒绝(3)：重置为待审批，教练可重新看到
        existing.status = 1
        existing.cancel_reason = ""
        await db.commit()
        return success({"reservation_id": existing.id}, "申请成功，等待教练确认")

    reservation = await create_reservation(db, current_user["user_id"], course_id)
    return success({"reservation_id": reservation.id}, "申请成功，等待教练确认")


@router.delete("/reservations/{reservation_id}")
async def cancel(
    reservation_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消预约（待审批或已确认均可取消）"""
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation or reservation.user_id != current_user["user_id"]:
        return json_fail("预约记录不存在", 404)
    if reservation.status not in (1, 2):
        return json_fail("当前状态不可取消", 400)
    await cancel_reservation(db, reservation)
    return success(None, "已取消")
