# CRUD/course.py
# 课程与预约数据库操作，路由层调用这里，不直接写 SQL
# 课程：get_courses / get_course_by_id / create_course / get_coach_courses /
#        update_course / soft_delete_course / get_admin_courses / review_course / offline_course
# 预约：get_reservation / create_reservation / get_user_reservations /
#        cancel_reservation / get_course_reservations / approve_reservation

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.course import Course, Reservation
from models.user import User


# ── 课程 ──────────────────────────────────────────────────────────────────────

async def get_courses(db: AsyncSession, category=None, keyword=None, page=1, page_size=12):
    """用户端：获取招募中(1)和满员(2)的课程，按开始时间升序"""
    where = [Course.status.in_([1, 2]), Course.is_deleted == 0]
    if category:
        where.append(Course.category == category)
    if keyword:
        where.append(Course.title.contains(keyword))

    total = (await db.execute(select(func.count(Course.id)).where(*where))).scalar()
    result = await db.execute(
        select(Course).where(*where)
        .order_by(Course.start_time.asc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def get_course_by_id(db: AsyncSession, course_id: int):
    """按 ID 查课程（含软删除过滤）"""
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def create_course(db: AsyncSession, coach_id: int, data: dict):
    """教练创建课程，初始状态为待审核(0)"""
    # start_time/end_time 由字符串转 datetime
    if data.get("start_time"):
        data["start_time"] = datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
    if data.get("end_time"):
        data["end_time"] = datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
    else:
        data.pop("end_time", None)

    course = Course(coach_id=coach_id, status=0, **data)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def get_coach_courses(db: AsyncSession, coach_id: int):
    """教练查自己发布的全部课程，附带每门课待审批预约数"""
    result = await db.execute(
        select(Course, func.count(Reservation.id).label("pending_count"))
        .outerjoin(
            Reservation,
            (Reservation.course_id == Course.id) & (Reservation.status == 1)
        )
        .where(Course.coach_id == coach_id, Course.is_deleted == 0)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
    )
    return result.all()  # 每行为 (Course, pending_count)


async def update_course(db: AsyncSession, course: Course, fields: dict):
    """更新被驳回的课程，重置为待审核(0)，清空驳回原因"""
    for k, v in fields.items():
        if v is None:
            continue
        if k in ("start_time", "end_time") and isinstance(v, str):
            v = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        setattr(course, k, v)
    course.status = 0
    course.reject_reason = ""
    await db.commit()


async def soft_delete_course(db: AsyncSession, course: Course):
    """软删除"""
    course.is_deleted = 1
    await db.commit()


async def get_admin_courses(db: AsyncSession, status=None, page=1, page_size=20):
    """管理员查课程列表，含教练昵称"""
    where = [Course.is_deleted == 0]
    if status is not None:
        where.append(Course.status == status)

    total = (await db.execute(select(func.count(Course.id)).where(*where))).scalar()
    result = await db.execute(
        select(Course, User.nickname)
        .join(User, Course.coach_id == User.id)
        .where(*where)
        .order_by(Course.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return result.all(), total


async def review_course(db: AsyncSession, course: Course, status: int,
                        reject_reason: str, admin_id: int):
    """审核课程：通过(1) 或 驳回(4)"""
    course.status = status
    course.reject_reason = reject_reason or ""
    course.reviewed_by = admin_id
    course.reviewed_at = datetime.now()
    await db.commit()


async def offline_course(db: AsyncSession, course: Course):
    """下架课程：status=5"""
    course.status = 5
    await db.commit()


# ── 预约 ──────────────────────────────────────────────────────────────────────

async def get_reservation(db: AsyncSession, user_id: int, course_id: int):
    """查询用户对某课程的最新预约记录（按 id 倒序取第一条）"""
    result = await db.execute(
        select(Reservation).where(
            Reservation.user_id == user_id,
            Reservation.course_id == course_id
        ).order_by(Reservation.id.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def get_reservation_by_id(db: AsyncSession, reservation_id: int):
    """按 ID 查预约记录"""
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    return result.scalar_one_or_none()


async def create_reservation(db: AsyncSession, user_id: int, course_id: int):
    """创建预约，初始状态为待审批(1)"""
    reservation = Reservation(user_id=user_id, course_id=course_id, status=1)
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def get_user_reservations(db: AsyncSession, user_id: int):
    """用户查自己的全部预约记录，含课程和教练信息"""
    # 三表 JOIN：Reservation → Course → User(教练)
    CoachUser = User.__class__.__mro__  # 仅用于别名，实际用 aliased
    from sqlalchemy.orm import aliased
    CoachAlias = aliased(User)

    result = await db.execute(
        select(Reservation, Course.title, Course.start_time, Course.location, CoachAlias.nickname)
        .join(Course, Reservation.course_id == Course.id)
        .join(CoachAlias, Course.coach_id == CoachAlias.id)
        .where(Reservation.user_id == user_id)
        .order_by(Reservation.created_at.desc())
    )
    return result.all()


async def cancel_reservation(db: AsyncSession, reservation: Reservation):
    """
    取消预约：status=0。
    若原为已确认(2)，则对应课程 enrolled-1；
    若课程因此从满员(2)变为有空位，恢复为招募中(1)。
    """
    was_confirmed = reservation.status == 2
    reservation.status = 0
    await db.commit()

    if was_confirmed:
        course = await db.get(Course, reservation.course_id)
        if course:
            course.enrolled = max(0, course.enrolled - 1)
            # 满员课程取消后恢复招募中
            if course.status == 2:
                course.status = 1
            await db.commit()


async def get_course_reservations(db: AsyncSession, course_id: int):
    """教练查某课程的全部预约申请，含用户昵称"""
    result = await db.execute(
        select(Reservation, User.nickname)
        .join(User, Reservation.user_id == User.id)
        .where(Reservation.course_id == course_id)
        .order_by(Reservation.created_at.desc())
    )
    return result.all()


async def approve_reservation(db: AsyncSession, reservation: Reservation,
                               status: int, cancel_reason: str, course: Course):
    """
    教练审批预约：确认(2) 或 拒绝(3)。
    确认时 course.enrolled+1，若达到 max_people 则课程变为满员(2)。
    """
    reservation.status = status
    reservation.cancel_reason = cancel_reason or ""
    await db.commit()

    if status == 2:
        course.enrolled += 1
        if course.enrolled >= course.max_people:
            course.status = 2  # 满员
        await db.commit()
