from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_student, require_teacher
from app.models import User
from app.schemas.classes import ClassCreate, ClassOut, JoinIn
from app.services import classes as svc

router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(body: ClassCreate, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> ClassOut:
    klass = svc.create_class(db, user, body.name, body.course_id)
    db.commit()
    return svc.class_out(db, klass)


@router.get("/mine", response_model=list[ClassOut])
def my_classes(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ClassOut]:
    return [svc.class_out(db, k) for k in svc.classes_for(db, user)]


@router.post("/join", response_model=ClassOut)
def join(body: JoinIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> ClassOut:
    klass = svc.join_class(db, user, body.code)
    db.commit()
    return svc.class_out(db, klass)
