# api/coach_course.py
# 教练端课程管理接口（需 coach 角色）
# POST   /coach/courses/upload/cover          上传封面图
# POST   /coach/courses                       发布课程（status=0 待审核）
# GET    /coach/courses                       我的课程列表
# PUT    /coach/courses/{id}                  修改被驳回的课程
# DELETE /coach/courses/{id}                  删除待审核/已驳回的课程
# GET    /coach/courses/{id}/reservations     课程预约申请列表
# PUT    /coach/courses/reservations/{id}     审批预约（确认/拒绝）

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.course import CourseCreate, CourseUpdate, ReservationAction
from CRUD.course import (
    create_course, get_coach_courses, get_course_by_id,
    update_course, soft_delete_course,
    get_course_reservations, get_reservation_by_id, approve_reservation,
)
from utils.deps import get_current_user
from utils.response import success, json_fail

router = APIRouter(prefix="/coach/courses", tags=["coach-courses"])

_COVER_DIR   = Path("static/course_covers")
_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
_COVER_EXT   = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_COVER   = 5 * 1024 * 1024

_COVER_DIR.mkdir(parents=True, exist_ok=True)


def _require_coach(current_user: dict):
    if current_user.get("role") != "coach":
        return json_fail("无权限", 403)


@router.post("/upload/cover")
async def upload_cover(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传课程封面图，返回相对路径供发布时填入 cover_img"""
    err = _require_coach(current_user)
    if err:
        return err
    if file.content_type not in _COVER_TYPES:
        return json_fail("封面图请上传 JPG、PNG 或 WebP 格式", 400)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _COVER_EXT:
        ext = ".jpg"
    raw = await file.read()
    if len(raw) > _MAX_COVER:
        return json_fail("封面图不能超过 5MB", 400)
    safe_name = f"{current_user['user_id']}_{uuid4().hex}{ext}"
    (_COVER_DIR / safe_name).write_bytes(raw)
    return success({"path": f"course_covers/{safe_name}"}, "上传成功")


@router.post("")
async def publish_course(
    form: CourseCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布新课程，初始状态为待审核"""
    err = _require_coach(current_user)
    if err:
        return err
    course = await create_course(db, current_user["user_id"], form.model_dump())
    return success({"id": course.id}, "提交成功，等待审核")

# 教练端课程发布列表获取接口
@router.get("")
async def my_courses(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我发布的全部课程，含每门课待审批预约数"""
    err = _require_coach(current_user)
    if err:
        return err
    rows = await get_coach_courses(db, current_user["user_id"])
    return success([{
        "id": c.id,
        "title": c.title,
        "category": c.category,
        "difficulty": c.difficulty,
        "cover_img": c.cover_img or "",
        "price": str(c.price),
        "max_people": c.max_people,
        "enrolled": c.enrolled,
        "start_time": c.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": c.end_time.strftime("%Y-%m-%d %H:%M:%S") if c.end_time else "",
        "location": c.location,
        "description": c.description or "",
        "status": c.status,
        "reject_reason": c.reject_reason,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "pending_count": pending,  # 待审批预约数，用于前端红点
    } for c, pending in rows])


@router.put("/reservations/{reservation_id}")
async def approve(
    reservation_id: int,
    form: ReservationAction,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """审批预约：2=确认 3=拒绝"""
    err = _require_coach(current_user)
    if err:
        return err
    if form.status not in (2, 3):
        return json_fail("status 只能为 2(确认) 或 3(拒绝)", 400)

    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        return json_fail("预约记录不存在", 404)
    if reservation.status != 1:
        return json_fail("只能审批待审批状态的预约", 400)

    course = await get_course_by_id(db, reservation.course_id)
    if not course or course.coach_id != current_user["user_id"]:
        return json_fail("无权限操作此预约", 403)

    if form.status == 2 and course.enrolled >= course.max_people:
        return json_fail("课程已满员，无法确认", 400)

    await approve_reservation(db, reservation, form.status, form.cancel_reason, course)
    msg = "已确认" if form.status == 2 else "已拒绝"
    return success(None, msg)


@router.get("/{course_id}/reservations")
async def course_reservations(
    course_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看某课程的全部预约申请"""
    err = _require_coach(current_user)
    if err:
        return err
    course = await get_course_by_id(db, course_id)
    if not course or course.coach_id != current_user["user_id"]:
        return json_fail("课程不存在", 404)
    rows = await get_course_reservations(db, course_id)
    return success([{
        "reservation_id": r.id,
        "user_id": r.user_id,
        "user_name": nickname or "",
        "status": r.status,
        "cancel_reason": r.cancel_reason,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for r, nickname in rows])


@router.put("/{course_id}")
async def edit_course(
    course_id: int,
    form: CourseUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改被驳回的课程并重新提交审核"""
    err = _require_coach(current_user)
    if err:
        return err
    course = await get_course_by_id(db, course_id)
    if not course or course.coach_id != current_user["user_id"]:
        return json_fail("课程不存在", 404)
    if course.status != 4:
        return json_fail("只能修改已驳回的课程", 400)
    await update_course(db, course, form.model_dump(exclude_unset=True))
    return success(None, "已重新提交审核")


@router.delete("/{course_id}")
async def delete_course(
    course_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除待审核或已驳回的课程"""
    err = _require_coach(current_user)
    if err:
        return err
    course = await get_course_by_id(db, course_id)
    if not course or course.coach_id != current_user["user_id"]:
        return json_fail("课程不存在", 404)
    if course.status not in (0, 4):
        return json_fail("只能删除待审核或已驳回的课程", 400)
    await soft_delete_course(db, course)
    return success(None, "已删除")

