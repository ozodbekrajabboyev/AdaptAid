"""Student-facing learning loop: onboarding, recommendations, aid events, quizzes, own progress."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_student
from app.models import User
from app.schemas.learning import (
    AnswerIn,
    AnswerOut,
    AttemptOut,
    EventIn,
    EventOut,
    FinishOut,
    IlsIn,
    ImpressionIn,
    OnboardingStatus,
    QuestionnaireIn,
    QuestionnaireOut,
    QuizStartIn,
    RecListOut,
    RefreshIn,
    StyleOut,
)
from app.services import events as events_svc
from app.services import me as me_svc
from app.services import onboarding as onboarding_svc
from app.services import quiz as quiz_svc
from app.services import recommend as rec_svc
from app.services import study as study_svc

router = APIRouter(tags=["learning"])


# ---------------------------------------------------------------- onboarding


@router.get("/onboarding/status", response_model=OnboardingStatus)
def onboarding_status(db: Session = Depends(get_db), user: User = Depends(require_student)) -> OnboardingStatus:
    return onboarding_svc.status_for(db, user)


@router.get("/onboarding/questionnaire", response_model=QuestionnaireOut)
def questionnaire(db: Session = Depends(get_db), _: User = Depends(require_student)) -> QuestionnaireOut:
    return onboarding_svc.questionnaire(db)


@router.post("/onboarding/questionnaire", response_model=StyleOut)
def submit_questionnaire(body: QuestionnaireIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> StyleOut:
    out = onboarding_svc.submit_questionnaire(db, user, body.answers)
    db.commit()
    return out


@router.post("/onboarding/ils", response_model=StyleOut)
def submit_ils(body: IlsIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> StyleOut:
    out = onboarding_svc.submit_ils(db, user, body.model_dump())
    db.commit()
    return out


@router.post("/onboarding/consent", status_code=status.HTTP_204_NO_CONTENT)
def consent(db: Session = Depends(get_db), user: User = Depends(require_student)) -> None:
    study_svc.give_consent(db, user)
    enrollment = quiz_svc.enrollment_or_none(db, user)
    if enrollment:
        study_svc.ensure_form_order(db, enrollment)
    db.commit()


# ---------------------------------------------------------------- recommendations


@router.get("/recommendations/current", response_model=RecListOut)
def current_list(concept_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_student)) -> RecListOut:
    lst = rec_svc.current(db, user, concept_id)
    db.commit()
    return rec_svc.to_out(db, user, lst)


@router.post("/recommendations/refresh", response_model=RecListOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> RecListOut:
    lst = rec_svc.generate(db, user, "manual", body.concept_id)
    db.commit()
    return rec_svc.to_out(db, user, lst)


@router.post("/recommendations/impression", status_code=status.HTTP_204_NO_CONTENT)
def impression(body: ImpressionIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> None:
    rec_svc.mark_impression(db, user, body.list_id)
    db.commit()


# ---------------------------------------------------------------- events


@router.post("/events", response_model=EventOut)
def event(body: EventIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> EventOut:
    out = events_svc.record(db, user, body)
    db.commit()
    return out


# ---------------------------------------------------------------- quizzes


@router.post("/quiz/start", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def quiz_start(body: QuizStartIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> AttemptOut:
    out = quiz_svc.start(db, user, body.kind, body.concept_id, body.use_id, body.aid_id)
    db.commit()
    return out


@router.get("/quiz/attempts/{attempt_id}", response_model=AttemptOut)
def quiz_get(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(require_student)) -> AttemptOut:
    return quiz_svc.attempt_out(db, user, attempt_id)


@router.post("/quiz/attempts/{attempt_id}/answer", response_model=AnswerOut)
def quiz_answer(attempt_id: int, body: AnswerIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> AnswerOut:
    out = quiz_svc.answer(db, user, attempt_id, body.question_id, body.chosen_index, body.time_ms)
    db.commit()
    return out


@router.post("/quiz/attempts/{attempt_id}/finish", response_model=FinishOut)
def quiz_finish(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(require_student)) -> FinishOut:
    out = quiz_svc.finish(db, user, attempt_id)
    db.commit()
    return out


# ---------------------------------------------------------------- pilot study


class SurveyIn(BaseModel):
    sus: list[int] = Field(min_length=10, max_length=10)
    satisfaction: list[int] = Field(min_length=5, max_length=5)
    comment: str = Field(default="", max_length=2000)


@router.get("/study/status")
def study_status(db: Session = Depends(get_db), user: User = Depends(require_student)) -> dict:
    return study_svc.status(db, user)


@router.get("/study/survey")
def study_survey(db: Session = Depends(get_db), _: User = Depends(require_student)) -> dict:
    from app.services import settings as settings_svc

    value, _v = settings_svc.get(db, settings_svc.SUS)
    return value


@router.post("/study/posttest", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def start_posttest(db: Session = Depends(get_db), user: User = Depends(require_student)) -> AttemptOut:
    s = study_svc.status(db, user)
    if not s["posttest_open"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "The post-test is not open for you.")
    if s["posttest_done"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already taken the post-test.")
    from app.models.base import AttemptKind

    out = quiz_svc.start(db, user, AttemptKind.posttest)
    db.commit()
    return out


@router.post("/study/survey", status_code=status.HTTP_201_CREATED)
def submit_survey(body: SurveyIn, db: Session = Depends(get_db), user: User = Depends(require_student)) -> dict:
    if study_svc.status(db, user)["survey_done"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already answered the survey.")
    try:
        score = study_svc.save_survey(db, user, body.sus, body.satisfaction, body.comment)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    db.commit()
    return {"sus": score}


# ---------------------------------------------------------------- me


@router.get("/me/summary", response_model=me_svc.SummaryOut)
def my_summary(db: Session = Depends(get_db), user: User = Depends(require_student)) -> me_svc.SummaryOut:
    return me_svc.summary(db, user)


@router.get("/me/path", response_model=me_svc.PathOut)
def my_path(db: Session = Depends(get_db), user: User = Depends(require_student)) -> me_svc.PathOut:
    return me_svc.path(db, user)


@router.get("/me/progress", response_model=me_svc.ProgressOut)
def my_progress(db: Session = Depends(get_db), user: User = Depends(require_student)) -> me_svc.ProgressOut:
    return me_svc.progress(db, user)


@router.get("/me/history", response_model=list[me_svc.HistoryItem])
def my_history(db: Session = Depends(get_db), user: User = Depends(require_student)) -> list[me_svc.HistoryItem]:
    return me_svc.history(db, user)
