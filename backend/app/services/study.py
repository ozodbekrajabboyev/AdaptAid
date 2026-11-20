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
