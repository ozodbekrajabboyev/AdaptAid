from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_teacher
from app.models import Course, Question, TeachingAid, User
from app.models.base import QuestionPool
from app.schemas.content import (
    AidDetail,
    AidIn,
    AidSummary,
    ConceptOut,
    CourseOut,
    ImportResult,
    QuestionIn,
    QuestionOut,
)
from app.services import content as svc

router = APIRouter(tags=["content"])
MAX_UPLOAD = 2_000_000


@router.get("/courses", response_model=list[CourseOut])
def courses(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.id)))


@router.get("/courses/{course_id}/concepts", response_model=list[ConceptOut])
def concepts(course_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ConceptOut]:
    return svc.list_concepts(db, course_id)


@router.get("/aids", response_model=list[AidSummary])
def aids(
    course_id: int | None = None,
    concept_id: int | None = None,
    aid_type: str | None = Query(None, alias="type"),
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AidSummary]:
    return svc.list_aids(db, course_id, concept_id, aid_type, q)


@router.get("/aids/{aid_id}", response_model=AidDetail)
def aid(aid_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> AidDetail:
    return svc.aid_detail(db, aid_id)


@router.post("/aids", response_model=AidDetail, status_code=status.HTTP_201_CREATED)
def create_aid(body: AidIn, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> AidDetail:
    a = svc.save_aid(db, body, user.id)
    db.commit()
    return svc.aid_detail(db, a.id)


@router.put("/aids/{aid_id}", response_model=AidDetail)
def update_aid(aid_id: int, body: AidIn, db: Session = Depends(get_db), user: User = Depends(require_teacher)) -> AidDetail:
    svc.save_aid(db, body, user.id, aid_id)
    db.commit()
    return svc.aid_detail(db, aid_id)


@router.delete("/aids/{aid_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_aid(aid_id: int, db: Session = Depends(get_db), _: User = Depends(require_teacher)) -> Response:
    a = db.get(TeachingAid, aid_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That teaching aid does not exist.")
    a.is_active = False  # archived, not deleted: past recommendations still refer to it
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/questions", response_model=list[QuestionOut])
def questions(
    concept_id: int | None = None,
    pool: QuestionPool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
) -> list[QuestionOut]:
    stmt = select(Question).where(Question.is_active)
    if concept_id:
        stmt = stmt.where(Question.concept_id == concept_id)
    if pool:
        stmt = stmt.where(Question.pool == pool)
    return [svc.question_out(q) for q in db.scalars(stmt.order_by(Question.key))]


@router.post("/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(body: QuestionIn, db: Session = Depends(get_db), _: User = Depends(require_teacher)) -> QuestionOut:
    q = svc.save_question(db, body)
    db.commit()
    return svc.question_out(q)


@router.put("/questions/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: int, body: QuestionIn, db: Session = Depends(get_db), _: User = Depends(require_teacher)
) -> QuestionOut:
    q = svc.save_question(db, body, question_id)
    db.commit()
    return svc.question_out(q)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_question(question_id: int, db: Session = Depends(get_db), _: User = Depends(require_teacher)) -> Response:
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That question does not exist.")
    q.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _csv(text: str, filename: str) -> PlainTextResponse:
    return PlainTextResponse(text, media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/content/export/aids.csv", response_class=PlainTextResponse)
def export_aids(course_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(require_teacher)):
    cid = course_id or svc.default_course(db).id
    return _csv(svc.export_aids_csv(db, cid), "aids.csv")


@router.get("/content/export/questions.csv", response_class=PlainTextResponse)
def export_questions(course_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(require_teacher)):
    cid = course_id or svc.default_course(db).id
    return _csv(svc.export_questions_csv(db, cid), "questions.csv")


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The file is larger than 2 MB.")
    return data


@router.post("/content/import/aids", response_model=ImportResult)
async def import_aids(
    file: UploadFile = File(...), course_id: int | None = None, db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
) -> ImportResult:
    data = await _read_upload(file)
    cid = course_id or svc.default_course(db).id
    result = svc.import_aids_csv(db, cid, data, user.id)
    db.commit()
    return result


@router.post("/content/import/questions", response_model=ImportResult)
async def import_questions(
    file: UploadFile = File(...), course_id: int | None = None, db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
) -> ImportResult:
    data = await _read_upload(file)
    cid = course_id or svc.default_course(db).id
    result = svc.import_questions_csv(db, cid, data)
    db.commit()
    return result
