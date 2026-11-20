"""Learner state: catalogue, mastery, preference profile, and the LearnerView the engine needs."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AidStats,
    AidUse,
    Concept,
    ConceptPrerequisite,
    Course,
    Enrollment,
    LearnerFeatures,
    Mastery,
    SchoolClass,
    StyleProfile,
    TeachingAid,
    User,
)
from app.models.base import Arm, CheckStatus
from app.services import content as content_svc
from app.services import model_store
from engine.bkt import BKTParams
from engine.types import AidInfo, Catalogue, LearnerView

COOLDOWN = 4  # an aid is not recommended again until 4 other aids have been opened
MIN_PEER_N = 5


def course_for(db: Session, user: User) -> Course:
    row = db.execute(
        select(Course).join(SchoolClass, SchoolClass.course_id == Course.id)
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
        .where(Enrollment.user_id == user.id).order_by(Enrollment.joined_at)
    ).scalars().first()
    return row or content_svc.default_course(db)


def enrollment_for(db: Session, user: User) -> Enrollment | None:
    return db.scalars(select(Enrollment).where(Enrollment.user_id == user.id).order_by(Enrollment.joined_at)).first()


def arm_for(db: Session, user: User) -> Arm:
    e = enrollment_for(db, user)
    return e.arm if e and e.arm else Arm.adaptive


_catalogue_cache: dict[int, tuple[tuple, Catalogue]] = {}


def _catalogue_token(db: Session, course_id: int) -> tuple:
    from sqlalchemy import func

    aid_row = db.execute(select(func.count(TeachingAid.id), func.max(TeachingAid.updated_at))
                         .where(TeachingAid.course_id == course_id, TeachingAid.is_active)).one()
    concept_row = db.execute(select(func.count(Concept.id), func.sum(Concept.params_version))
                             .where(Concept.course_id == course_id)).one()
    return (tuple(aid_row), tuple(concept_row))


def load_catalogue(db: Session, course_id: int) -> Catalogue:
    """The engine's view of a course, cached until aids or BKT parameters change."""
    token = _catalogue_token(db, course_id)
    hit = _catalogue_cache.get(course_id)
    if hit and hit[0] == token:
        return hit[1]
    cat = _load_catalogue(db, course_id)
    _catalogue_cache[course_id] = (token, cat)
    return cat


def _load_catalogue(db: Session, course_id: int) -> Catalogue:
    concepts = sorted(db.scalars(select(Concept).where(Concept.course_id == course_id)), key=lambda c: c.order_index)
    ids = [c.id for c in concepts]
    prereqs: dict[int, set[int]] = {c: set() for c in ids}
    for row in db.scalars(select(ConceptPrerequisite).where(ConceptPrerequisite.concept_id.in_(ids))):
        prereqs[row.concept_id].add(row.prereq_id)
    aids_rows = list(db.scalars(select(TeachingAid).where(TeachingAid.course_id == course_id, TeachingAid.is_active)))
    primary = content_svc.primary_concepts(db, [a.id for a in aids_rows])
    aids = {
        a.id: AidInfo(
            id=a.id, concept_id=primary[a.id], aid_type=a.aid_type.value,
            style=(a.style_ar, a.style_si, a.style_vv, a.style_sg), difficulty=a.difficulty,
            default_order=a.default_order, title=a.title,
        )
        for a in aids_rows
        if a.id in primary
    }
    return Catalogue(
        syllabus=ids,
        prereqs=prereqs,
        aids=aids,
        names={c.id: c.name for c in concepts},
        params={c.id: BKTParams(c.bkt_prior, c.bkt_learn, c.bkt_guess, c.bkt_slip) for c in concepts},
    )


def mastery_map(db: Session, user_id: int, cat: Catalogue) -> dict[int, float]:
    rows = {m.concept_id: m.p_known for m in db.scalars(select(Mastery).where(Mastery.user_id == user_id))}
    return {c: rows.get(c, cat.bkt(c).prior) for c in cat.syllabus}


def style_profile(db: Session, user_id: int) -> StyleProfile | None:
    return db.get(StyleProfile, user_id)


def style_vector(profile: StyleProfile | None) -> tuple[float, float, float, float]:
    if profile is None:
        return (0.0, 0.0, 0.0, 0.0)
    return (profile.ar, profile.si, profile.vv, profile.sg)


def persona_of(db: Session, user_id: int) -> str | None:
    lf = db.get(LearnerFeatures, user_id)
    return lf.persona if lf else None


def use_value(use: AidUse) -> float:
    """How much an aid helped one learner (the CF matrix value)."""
    if use.check_status == CheckStatus.done and use.gain is not None:
        value = max(0.0, use.gain)
    elif use.completed_at is not None:
        value = 0.15
    else:
        value = 0.0
    if use.rating is not None and use.rating >= 4:
        value += 0.1
    return round(value, 4)


def help_scores(db: Session, persona: str | None) -> dict[int, float]:
    overall = {s.aid_id: s.smoothed_gain for s in db.scalars(select(AidStats).where(AidStats.persona == ""))}
    if persona:
        for s in db.scalars(select(AidStats).where(AidStats.persona == persona)):
            if s.n_checked >= MIN_PEER_N:
                overall[s.aid_id] = s.smoothed_gain
    return overall


def build_view(db: Session, user: User, cat: Catalogue) -> LearnerView:
    mastery = mastery_map(db, user.id, cat)
    uses = list(db.scalars(select(AidUse).where(AidUse.user_id == user.id).order_by(AidUse.opened_at, AidUse.id)))
    formats = Counter(cat.aids[u.aid_id].aid_type for u in uses if u.aid_id in cat.aids)
    per_concept = Counter(u.concept_id for u in uses)
    recent = {u.aid_id for u in uses[-COOLDOWN:]}
    history: dict[int, float] = {}
    best: dict[int, tuple[float, int]] = {}
    for u in uses:
        v = use_value(u)
        history[u.aid_id] = max(history.get(u.aid_id, 0.0), v)
        if u.gain is not None and (u.concept_id not in best or u.gain > best[u.concept_id][0]):
            best[u.concept_id] = (u.gain, u.aid_id)

    from app.models import Attempt
    from app.models.base import AttemptKind

    passed = {
        a.concept_id
        for a in db.scalars(select(Attempt).where(Attempt.user_id == user.id, Attempt.kind == AttemptKind.check,
                                                   Attempt.finished_at.is_not(None)))
        if a.concept_id and a.n_total and a.n_correct / a.n_total >= 2 / 3
    }
    model, _ = model_store.latest_cf(db)
    cf_scores = model.score(history, list(cat.aids)) if model else {}
    return LearnerView(
        mastery=mastery,
        style=style_vector(style_profile(db, user.id)),
        n_uses=len(uses),
        format_counts=dict(formats),
        recent_aids=recent,
        used_aids=set(history),
        passed_check=passed,
        aids_used_per_concept=dict(per_concept),
        cf_scores=cf_scores,
        help_scores=help_scores(db, persona_of(db, user.id)),
        best_gain_aid={c: aid for c, (_, aid) in best.items()},
    )
