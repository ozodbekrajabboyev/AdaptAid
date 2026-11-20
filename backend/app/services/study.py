"""Pilot study: consent, counterbalanced forms, arm assignment after the pre-test."""

from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, Consent, Enrollment, User
from app.models.base import Arm, AttemptKind
from app.services import learner as learner_svc
from app.services import settings as settings_svc
from engine import clock


def study_settings(db: Session) -> dict:
    value, _ = settings_svc.get(db, settings_svc.STUDY)
    return value


def is_active(db: Session) -> bool:
    return bool(study_settings(db).get("active"))


def has_consent(db: Session, user: User) -> bool:
    return db.get(Consent, user.id) is not None


def give_consent(db: Session, user: User) -> None:
    if not has_consent(db, user):
        db.add(Consent(user_id=user.id, version=str(study_settings(db).get("consent_version", "1.0")),
                       consented_at=clock.now()))
        db.flush()


def ensure_form_order(db: Session, enrollment: Enrollment) -> str:
    """Counterbalance: alternate A->B and B->A within each class by enrolment order."""
    if enrollment.form_order:
        return enrollment.form_order
    n_ab = len(db.scalars(select(Enrollment).where(Enrollment.class_id == enrollment.class_id,
                                                   Enrollment.form_order == "AB")).all())
    n_ba = len(db.scalars(select(Enrollment).where(Enrollment.class_id == enrollment.class_id,
                                                   Enrollment.form_order == "BA")).all())
    enrollment.form_order = "AB" if n_ab <= n_ba else "BA"
    db.flush()
    return enrollment.form_order


def pretest_done(db: Session, user: User) -> bool:
    return db.scalar(select(Attempt.id).where(Attempt.user_id == user.id, Attempt.kind == AttemptKind.pretest,
                                              Attempt.finished_at.is_not(None))) is not None


def assign_arm_after_pretest(db: Session, user: User, attempt: Attempt) -> Arm | None:
    """Stratified randomisation: within the class and the learner's pre-test score band,
    put the learner in the arm that has fewer members so far (random on ties)."""
    enrollment = learner_svc.enrollment_for(db, user)
    if enrollment is None or enrollment.arm is not None or not is_active(db):
        return enrollment.arm if enrollment else None
    band = _band(attempt.n_correct, attempt.n_total)
    peers = db.execute(
        select(Enrollment, Attempt)
        .join(Attempt, (Attempt.user_id == Enrollment.user_id) & (Attempt.kind == AttemptKind.pretest)
              & Attempt.finished_at.is_not(None))
        .where(Enrollment.class_id == enrollment.class_id, Enrollment.arm.is_not(None))
    ).all()
    counts = {Arm.adaptive: 0, Arm.control: 0}
    for e, a in peers:
        if _band(a.n_correct, a.n_total) == band:
            counts[e.arm] += 1
    if counts[Arm.adaptive] == counts[Arm.control]:
        arm = random.Random(f"{user.id}-{attempt.id}").choice([Arm.adaptive, Arm.control])
    else:
        arm = min(counts, key=counts.get)  # type: ignore[arg-type]
    enrollment.arm = arm
    db.flush()
    return arm


def _band(n_correct: int, n_total: int) -> int:
    if not n_total:
        return 0
    share = n_correct / n_total
    return 0 if share < 0.34 else 1 if share < 0.67 else 2


# --------------------------------------------------------------------------- post-test, surveys, export



def sus_score(answers: list[int]) -> float:
    """Brooke (1996): odd items contribute (a - 1), even items (5 - a); the sum times 2.5 gives 0-100."""
    if len(answers) != 10 or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError("SUS needs ten answers from 1 to 5")
    total = sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers))
    return total * 2.5


def attempt_done(db: Session, user: User, kind: AttemptKind) -> Attempt | None:
    return db.scalars(select(Attempt).where(Attempt.user_id == user.id, Attempt.kind == kind,
                                            Attempt.finished_at.is_not(None)).order_by(Attempt.id)).first()


def status(db: Session, user: User) -> dict:
    from app.models import SurveyResponse
    from app.models.base import SurveyKind

    s = study_settings(db)
    enrollment = learner_svc.enrollment_for(db, user)
    in_study = bool(s.get("active")) and enrollment is not None and has_consent(db, user)
    pre = attempt_done(db, user, AttemptKind.pretest)
    post = attempt_done(db, user, AttemptKind.posttest)
    survey = db.scalar(select(SurveyResponse.id).where(SurveyResponse.user_id == user.id,
                                                       SurveyResponse.kind == SurveyKind.sus))
    return {
        "active": bool(s.get("active")),
        "participating": in_study,
        "pretest_done": pre is not None,
        "posttest_open": bool(s.get("posttest_open")) and in_study and pre is not None,
        "posttest_done": post is not None,
        "survey_done": survey is not None,
    }


def save_survey(db: Session, user: User, sus: list[int], satisfaction: list[int], comment: str) -> float:
    from app.models import SurveyResponse
    from app.models.base import SurveyKind

    score = sus_score(sus)
    if len(satisfaction) != 5 or any(a not in (1, 2, 3, 4, 5) for a in satisfaction):
        raise ValueError("The satisfaction questions need five answers from 1 to 5")
    now = clock.now()
    db.add(SurveyResponse(user_id=user.id, kind=SurveyKind.sus, answers={"items": sus}, score=score, created_at=now))
    db.add(SurveyResponse(user_id=user.id, kind=SurveyKind.satisfaction,
                          answers={"items": satisfaction, "comment": comment[:2000]},
                          score=round(sum(satisfaction) / 5, 3), created_at=now))
    db.flush()
    return score


EXPORT_FIELDS = [
    "participant", "class", "arm", "form_order", "pre_correct", "pre_total", "pre_score", "post_correct", "post_total",
    "post_score", "normalized_gain", "aid_uses", "checked_uses", "mean_residual_gain", "completion_rate", "active_days",
    "sus", "satisfaction", "consented_at",
]


def export_rows(db: Session) -> list[dict]:
    """One row per consenting, non-simulated participant. No names or emails: pseudonymous ids P001..."""
    from app.models import AidUse, SchoolClass, SurveyResponse
    from app.models.base import SurveyKind

    consents = list(db.scalars(select(Consent).order_by(Consent.consented_at, Consent.user_id)))
    rows = []
    for n, c in enumerate(consents, start=1):
        user = db.get(User, c.user_id)
        if user is None or user.is_synthetic:
            continue
        e = learner_svc.enrollment_for(db, user)
        klass = db.get(SchoolClass, e.class_id) if e else None
        pre = attempt_done(db, user, AttemptKind.pretest)
        post = attempt_done(db, user, AttemptKind.posttest)
        pre_s = pre.n_correct / pre.n_total if pre and pre.n_total else None
        post_s = post.n_correct / post.n_total if post and post.n_total else None
        g = None
        if pre_s is not None and post_s is not None and pre_s < 1:
            g = (post_s - pre_s) / (1 - pre_s)
        uses = list(db.scalars(select(AidUse).where(AidUse.user_id == user.id)))
        gains = [u.gain for u in uses if u.gain is not None]
        sus = db.scalar(select(SurveyResponse.score).where(SurveyResponse.user_id == user.id, SurveyResponse.kind == SurveyKind.sus))
        sat = db.scalar(select(SurveyResponse.score).where(SurveyResponse.user_id == user.id,
                                                           SurveyResponse.kind == SurveyKind.satisfaction))
        days = {u.opened_at.date() for u in uses}
        rows.append({
            "participant": f"P{n:03d}", "class": klass.name if klass else "", "arm": e.arm.value if e and e.arm else "",
            "form_order": e.form_order if e else "",
            "pre_correct": pre.n_correct if pre else "", "pre_total": pre.n_total if pre else "",
            "pre_score": round(pre_s, 4) if pre_s is not None else "",
            "post_correct": post.n_correct if post else "", "post_total": post.n_total if post else "",
            "post_score": round(post_s, 4) if post_s is not None else "",
            "normalized_gain": round(g, 4) if g is not None else "",
            "aid_uses": len(uses), "checked_uses": len(gains),
            "mean_residual_gain": round(sum(gains) / len(gains), 4) if gains else "",
            "completion_rate": round(sum(1 for u in uses if u.completed_at) / len(uses), 4) if uses else "",
            "active_days": len(days), "sus": sus if sus is not None else "", "satisfaction": sat if sat is not None else "",
            "consented_at": c.consented_at.date().isoformat(),
        })
    return rows
