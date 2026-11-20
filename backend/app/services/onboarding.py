"""Onboarding: join class, consent and pre-test (pilot only), preference questionnaire, diagnostic."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, QuestionnaireResponse, StyleProfile, User
from app.models.base import AttemptKind, QuestionnaireSource
from app.schemas.learning import OnboardingStatus, QuestionnaireItemOut, QuestionnaireOut, StyleOut
from app.services import learner as learner_svc
from app.services import settings as settings_svc
from app.services import study as study_svc
from engine import clock
from engine.style import POLES, Item, dominant_pole, from_ils_scores, score_questionnaire


def status_for(db: Session, user: User) -> OnboardingStatus:
    enrollment = learner_svc.enrollment_for(db, user)
    in_class = enrollment is not None
    study = study_svc.is_active(db) and in_class
    consent_needed = study and not study_svc.has_consent(db, user)
    pretest_needed = study and not study_svc.pretest_done(db, user)
    q_done = db.get(StyleProfile, user.id) is not None
    diag_done = db.scalar(select(Attempt.id).where(Attempt.user_id == user.id, Attempt.kind == AttemptKind.diagnostic,
                                                   Attempt.finished_at.is_not(None))) is not None
    if consent_needed:
        step = "consent"
    elif pretest_needed:
        step = "pretest"
    elif not q_done:
        step = "questionnaire"
    elif not diag_done:
        step = "diagnostic"
    else:
        step = "done"
    consent_text = study_svc.study_settings(db).get("consent_text") if consent_needed else None
    return OnboardingStatus(in_class=in_class, consent_needed=consent_needed, pretest_needed=pretest_needed,
                            questionnaire_done=q_done, diagnostic_done=diag_done, next_step=step,
                            consent_text=consent_text)


def questionnaire(db: Session) -> QuestionnaireOut:
    value, _ = settings_svc.get(db, settings_svc.QUESTIONNAIRE)
    if not value:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The questionnaire has not been loaded. Run `adaptaid seed`.")
    return QuestionnaireOut(
        title=value.get("title", "How do you like to learn?"), intro=value.get("intro", ""), note=value.get("note", ""),
        items=[QuestionnaireItemOut(key=i["key"], prompt=i["prompt"], a=i["a"], b=i["b"]) for i in value["items"]],
    )


def _set_prior(db: Session, user: User, vector: list[float]) -> StyleProfile:
    profile = db.get(StyleProfile, user.id)
    if profile is None:
        profile = StyleProfile(user_id=user.id)
        db.add(profile)
    profile.ar, profile.si, profile.vv, profile.sg = vector
    profile.prior_ar, profile.prior_si, profile.prior_vv, profile.prior_sg = vector
    profile.n_updates, profile.ema_gain, profile.updated_at = 0, 0.0, clock.now()
    db.flush()
    return profile


def submit_questionnaire(db: Session, user: User, answers: dict[str, str]) -> StyleOut:
    value, _ = settings_svc.get(db, settings_svc.QUESTIONNAIRE)
    items = [Item(i["key"], i["dim"], int(i["a_pole"])) for i in value.get("items", [])]
    missing = [i.key for i in items if i.key not in answers]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Please answer all questions ({len(missing)} left).")
    vector = score_questionnaire(answers, items)
    db.add(QuestionnaireResponse(user_id=user.id, source=QuestionnaireSource.builtin, answers=answers, vector=vector,
                                 created_at=clock.now()))
    return style_out(_set_prior(db, user, vector))


def submit_ils(db: Session, user: User, scores: dict[str, tuple[int, str]]) -> StyleOut:
    try:
        vector = from_ils_scores(scores)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    db.add(QuestionnaireResponse(user_id=user.id, source=QuestionnaireSource.ils,
                                 answers={k: list(v) for k, v in scores.items()}, vector=vector, created_at=clock.now()))
    return style_out(_set_prior(db, user, vector))


def style_out(profile: StyleProfile | None) -> StyleOut:
    vec = learner_svc.style_vector(profile)
    prior = [profile.prior_ar, profile.prior_si, profile.prior_vv, profile.prior_sg] if profile else [0.0] * 4
    pole = dominant_pole(vec)
    return StyleOut(vector=[round(x, 4) for x in vec], prior=[round(x, 4) for x in prior],
                    n_updates=profile.n_updates if profile else 0, dominant=pole[1] if pole else None,
                    labels=[list(POLES[d]) for d in ("ar", "si", "vv", "sg")])
