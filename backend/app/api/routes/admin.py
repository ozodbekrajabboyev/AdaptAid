from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models import User
from app.models.base import Role
from app.services import admin as svc
from app.services import settings as settings_svc

router = APIRouter(prefix="/admin", tags=["admin"])
JobKind = Literal["all", "personas", "risk", "aid_stats", "cf", "bkt"]


@router.get("/users", response_model=list[svc.AdminUser])
def users(role: Role | None = None, q: str | None = None, include_synthetic: bool = False,
          db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[svc.AdminUser]:
    return svc.users(db, role, q, include_synthetic)


@router.post("/users", response_model=svc.AdminUser, status_code=status.HTTP_201_CREATED)
def create_user(body: svc.UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> svc.AdminUser:
    u = svc.create_user(db, body)
    db.commit()
    return svc.users(db, None, u.email, True)[0]


class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)


@router.post("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(user_id: int, body: PasswordIn, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> None:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That user does not exist.")
    u.password_hash = hash_password(body.password)
    db.commit()


class ActiveIn(BaseModel):
    active: bool


@router.post("/users/{user_id}/active", status_code=status.HTTP_204_NO_CONTENT)
def set_active(user_id: int, body: ActiveIn, db: Session = Depends(get_db), me: User = Depends(require_admin)) -> None:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That user does not exist.")
    if u.id == me.id and not body.active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "You cannot deactivate your own account.")
    u.is_active = body.active
    db.commit()


@router.get("/jobs", response_model=list[svc.RunOut])
def jobs(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[svc.RunOut]:
    return svc.runs(db)


@router.post("/jobs/{kind}", status_code=status.HTTP_202_ACCEPTED)
def run_job(kind: JobKind, _: User = Depends(require_admin)) -> dict:
    from app.jobs.runner import run_in_background

    run_in_background(kind, "admin")
    return {"started": kind}


@router.get("/model-report")
def model_report(include_synthetic: bool = True, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    return svc.model_report(db, include_synthetic)


class StudySettings(BaseModel):
    active: bool
    frozen: bool
    posttest_open: bool
    consent_version: str = Field(min_length=1, max_length=16)
    consent_text: str = Field(min_length=20)


@router.get("/study/export.csv")
def study_export(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    import csv
    import io

    from fastapi.responses import PlainTextResponse

    from app.services import study as study_svc

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=study_svc.EXPORT_FIELDS)
    w.writeheader()
    for row in study_svc.export_rows(db):
        w.writerow(row)
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="pilot_study.csv"'})


@router.get("/settings/study", response_model=StudySettings)
def get_study(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> StudySettings:
    value, _v = settings_svc.get(db, settings_svc.STUDY)
    return StudySettings(**{**settings_svc.DEFAULTS[settings_svc.STUDY], **value})


@router.put("/settings/study", response_model=StudySettings)
def put_study(body: StudySettings, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> StudySettings:
    settings_svc.put(db, settings_svc.STUDY, body.model_dump())
    db.commit()
    return body
