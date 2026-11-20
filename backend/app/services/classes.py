import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, SchoolClass, User
from app.models.base import Role
from app.schemas.classes import ClassOut
from engine import clock

# No 0/O or 1/I so codes are easy to read aloud in class.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_join_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        if not db.scalar(select(SchoolClass.id).where(SchoolClass.join_code == code)):
            return code


def create_class(db: Session, teacher: User, name: str, course_id: int) -> SchoolClass:
    if db.get(Course, course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That course does not exist.")
    klass = SchoolClass(
        name=name, course_id=course_id, teacher_id=teacher.id, join_code=new_join_code(db), created_at=clock.now()
    )
    db.add(klass)
    db.flush()
    return klass


def join_class(db: Session, student: User, code: str) -> SchoolClass:
    klass = db.scalar(select(SchoolClass).where(SchoolClass.join_code == code.strip().upper()))
    if klass is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No class uses that code. Check it with your teacher.")
    exists = db.get(Enrollment, {"class_id": klass.id, "user_id": student.id})
    if exists is None:
        db.add(Enrollment(class_id=klass.id, user_id=student.id, joined_at=clock.now()))
        db.flush()
    return klass


def class_out(db: Session, klass: SchoolClass) -> ClassOut:
    course = db.get(Course, klass.course_id)
    teacher = db.get(User, klass.teacher_id)
    n = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.class_id == klass.id)) or 0
    return ClassOut(
        id=klass.id,
        name=klass.name,
        course_id=klass.course_id,
        course_title=course.title if course else "",
        teacher_id=klass.teacher_id,
        teacher_name=teacher.full_name if teacher else "",
        join_code=klass.join_code,
        n_students=n,
        created_at=klass.created_at,
    )


def classes_for(db: Session, user: User) -> list[SchoolClass]:
    if user.role == Role.admin:
        stmt = select(SchoolClass)
    elif user.role == Role.teacher:
        stmt = select(SchoolClass).where(SchoolClass.teacher_id == user.id)
    else:
        stmt = select(SchoolClass).join(Enrollment).where(Enrollment.user_id == user.id)
    return list(db.scalars(stmt.order_by(SchoolClass.created_at)))


def teacher_can_view(db: Session, user: User, class_id: int) -> SchoolClass:
    klass = db.get(SchoolClass, class_id)
    if klass is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That class does not exist.")
    if user.role != Role.admin and klass.teacher_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not teach this class.")
    return klass
