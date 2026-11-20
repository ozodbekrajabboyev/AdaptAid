from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_teacher
from app.models import User
from app.services import classes as classes_svc
from app.services import content as content_svc
from app.services import teacher as svc

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/classes/{class_id}/overview", response_model=svc.OverviewOut)
def overview(class_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> svc.OverviewOut:
    return svc.overview(db, classes_svc.teacher_can_view(db, user, class_id))


@router.get("/classes/{class_id}/heatmap", response_model=svc.HeatmapOut)
def heatmap(class_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> svc.HeatmapOut:
    return svc.heatmap(db, classes_svc.teacher_can_view(db, user, class_id))


@router.get("/classes/{class_id}/at-risk", response_model=list[svc.RiskRow])
def at_risk(class_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> list[svc.RiskRow]:
    return svc.at_risk(db, classes_svc.teacher_can_view(db, user, class_id))


@router.get("/classes/{class_id}/suggestions", response_model=list[svc.SuggestionOut])
def suggestions(class_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> list[svc.SuggestionOut]:
    return svc.suggestions(db, classes_svc.teacher_can_view(db, user, class_id))


@router.get("/classes/{class_id}/students/{student_id}")
def student(class_id: int, student_id: int, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> dict:
    return svc.student_detail(db, classes_svc.teacher_can_view(db, user, class_id), student_id)


@router.get("/aid-effectiveness", response_model=list[svc.EffectivenessRow])
def effectiveness(course_id: int | None = None, db: Session = Depends(get_db),
                  _: User = Depends(require_teacher)) -> list[svc.EffectivenessRow]:
    return svc.effectiveness(db, course_id or content_svc.default_course(db).id)


@router.get("/personas")
def personas(db: Session = Depends(get_db), _: User = Depends(require_teacher)) -> dict:
    return svc.latest_personas_run(db) or {}
