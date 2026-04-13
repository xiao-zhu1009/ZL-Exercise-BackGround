# api/admin_course.py
# 管理员课程审核接口（需 admin 角色）
# GET /admin/courses                      全部课程列表，可按 status 筛选
# GET /admin/courses/{id}/detail          单条课程完整详情（不限状态）
# PUT /admin/courses/{id}/review          审核：status=1 通过，status=4 驳回
# PUT /admin/courses/{id}/offline         下架招募中/满员的课程

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.course import CourseReview
from CRUD.course import get_admin_courses, get_course_by_id, review_course, offline_course
from CRUD.user import get_user_by_id
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/admin/courses", tags=["admin-courses"])


def _require_admin(current_user: dict):
    if current_user.get("role") != "admin":
        return json_fail("无权限", 403)


@router.get("")
async def list_all_courses(
    status: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取全部课程列表，可按 status 筛选（0待审核 1招募中 2满员 3已结束 4已驳回 5已下架）"""
    err = _require_admin(current_user)
    if err:
        return err
    rows, total = await get_admin_courses(db, status, page, page_size)
    return success({
        "list": [{
            "id": c.id,
            "title": c.title,
            "category": c.category,
            "difficulty": c.difficulty,
            "price": str(c.price),
            "max_people": c.max_people,
            "enrolled": c.enrolled,
            "start_time": c.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "location": c.location,
            "status": c.status,
            "reject_reason": c.reject_reason,
            "coach_id": c.coach_id,
            "coach_name": nickname or "",
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        } for c, nickname in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{course_id}/detail")
async def course_detail(
    course_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员预览单条课程完整内容，不限状态"""
    err = _require_admin(current_user)
    if err:
        return err
    course = await get_course_by_id(db, course_id)
    if not course:
        return json_fail("课程不存在", 404)
    coach = await get_user_by_id(db, course.coach_id)
    return success({
        "id": course.id,
        "title": course.title,
        "category": course.category,
        "difficulty": course.difficulty,
        "description": course.description or "",
        "cover_img": course.cover_img,
        "price": str(course.price),
        "max_people": course.max_people,
        "enrolled": course.enrolled,
        "start_time": course.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": course.end_time.strftime("%Y-%m-%d %H:%M:%S") if course.end_time else "",
        "location": course.location,
        "status": course.status,
        "reject_reason": course.reject_reason,
        "coach_name": coach.nickname if coach else "",
        "created_at": course.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })


@router.put("/{course_id}/review")
async def review(
    course_id: int,
    form: CourseReview,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """审核课程：status=1 通过，status=4 驳回（驳回需填 reject_reason）"""
    err = _require_admin(current_user)
    if err:
        return err
    if form.status not in (1, 4):
        return json_fail("status 只能为 1(通过) 或 4(驳回)", 400)
    if form.status == 4 and not form.reject_reason:
        return json_fail("驳回必须填写原因", 400)

    course = await get_course_by_id(db, course_id)
    if not course:
        return json_fail("课程不存在", 404)
    if course.status != 0:
        return json_fail("只能审核待审核状态的课程", 400)

    await review_course(db, course, form.status, form.reject_reason, current_user["user_id"])
    msg = "已通过" if form.status == 1 else "已驳回"
    return success(None, msg)


@router.put("/{course_id}/offline")
async def offline(
    course_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下架招募中或满员的课程"""
    err = _require_admin(current_user)
    if err:
        return err
    course = await get_course_by_id(db, course_id)
    if not course:
        return json_fail("课程不存在", 404)
    if course.status not in (1, 2):
        return json_fail("只能下架招募中或满员的课程", 400)
    await offline_course(db, course)
    return success(None, "已下架")
