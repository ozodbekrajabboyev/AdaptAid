"""What a student sees about themselves: summary, learning path, progress and history."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AidUse, Concept, Response, TeachingAid, User
from app.schemas.learning import FocusOut, OnboardingStatus, StyleOut
from app.services import learner as learner_svc
from app.services import onboarding as onboarding_svc
from engine import clock
from engine.graph import layers, projected_route, status
from engine.hybrid import phase_for
from engine.policy import AdaptivePolicy, StaticPolicy


class MasteryOut(BaseModel):
    concept_id: int
    slug: str
    name: str
    p: float
    status: str
    order: int


class SummaryOut(BaseModel):
    course_id: int
    course_title: str
    mastery: list[MasteryOut]
    style: StyleOut
    focus: FocusOut | None
    streak_days: int
    n_uses: int
    n_checks: int
    phase: str
    mastered: int
    total_concepts: int
    onboarding: OnboardingStatus


class PathNode(BaseModel):
    id: int
    slug: str
    name: str
    p: float
    status: str
    layer: int
    order: int
    visited: bool
    projected_rank: int | None


class PathOut(BaseModel):
    nodes: list[PathNode]
    edges: list[tuple[int, int]]  # (prerequisite, concept)
    route: list[int]
    projected: list[int]


class ProgressPoint(BaseModel):
    t: str
    p: float


class ProgressSeries(BaseModel):
    concept_id: int
    name: str
    points: list[ProgressPoint]


class DailyPoint(BaseModel):
    date: str
    mean_mastery: float
    answers: int


class ProgressOut(BaseModel):
    series: list[ProgressSeries]
    daily: list[DailyPoint]


class HistoryItem(BaseModel):
    use_id: int
    aid_id: int
    title: str
    aid_type: str
    concept_name: str
    opened_at: str
    completed: bool
    rating: int | None
    gain: float | None
    check_status: str


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().display_tz)


def streak_days(db: Session, user_id: int) -> int:
    days = {r.created_at.astimezone(_tz()).date() for r in db.scalars(select(Response).where(Response.user_id == user_id))}
    days |= {u.opened_at.astimezone(_tz()).date() for u in db.scalars(select(AidUse).where(AidUse.user_id == user_id))}
    today = clock.now().astimezone(_tz()).date()
    d, n = today, 0
    if d not in days:
        d -= timedelta(days=1)  # a streak survives until the end of today
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


def summary(db: Session, user: User) -> SummaryOut:
    course = learner_svc.course_for(db, user)
    cat = learner_svc.load_catalogue(db, course.id)
    mastery = learner_svc.mastery_map(db, user.id, cat)
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.course_id == course.id))}
    rows = [MasteryOut(concept_id=c, slug=concepts[c].slug, name=cat.names[c], p=round(mastery[c], 4),
                       status=status(c, mastery, cat.prereqs), order=i) for i, c in enumerate(cat.syllabus)]
    n_uses = len(db.scalars(select(AidUse.id).where(AidUse.user_id == user.id)).all())
    n_checks = len(db.scalars(select(AidUse.id).where(AidUse.user_id == user.id, AidUse.gain.is_not(None))).all())
    view = learner_svc.build_view(db, user, cat)
    policy = StaticPolicy() if learner_svc.arm_for(db, user).value == "control" else AdaptivePolicy()
    focus_id = policy.focus(view, cat)
    focus = None
    if focus_id is not None:
        focus = FocusOut(concept_id=focus_id, name=cat.names[focus_id], mastery=round(mastery[focus_id], 4),
                         minutes=12 + 3 * min(len(cat.aids_by_concept.get(focus_id, [])), 2))
    return SummaryOut(
        course_id=course.id, course_title=course.title, mastery=rows,
        style=onboarding_svc.style_out(learner_svc.style_profile(db, user.id)), focus=focus,
        streak_days=streak_days(db, user.id), n_uses=n_uses, n_checks=n_checks, phase=phase_for(n_uses),
        mastered=sum(1 for r in rows if r.status == "mastered"), total_concepts=len(rows),
        onboarding=onboarding_svc.status_for(db, user),
    )


def path(db: Session, user: User) -> PathOut:
    course = learner_svc.course_for(db, user)
    cat = learner_svc.load_catalogue(db, course.id)
    mastery = learner_svc.mastery_map(db, user.id, cat)
    edges = [(p, c) for c, ps in cat.prereqs.items() for p in ps]
    depth = layers(cat.syllabus, [(c, p) for p, c in edges])
    route: list[int] = []
    for u in db.scalars(select(AidUse).where(AidUse.user_id == user.id).order_by(AidUse.opened_at, AidUse.id)):
        if not route or route[-1] != u.concept_id:
            route.append(u.concept_id)
    projected = projected_route(cat.syllabus, mastery, cat.prereqs, cat.downstream, cat.order_index, steps=3)
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.course_id == course.id))}
    nodes = [PathNode(id=c, slug=concepts[c].slug, name=cat.names[c], p=round(mastery[c], 4),
                      status=status(c, mastery, cat.prereqs), layer=depth[c], order=i, visited=c in route,
                      projected_rank=projected.index(c) + 1 if c in projected else None)
             for i, c in enumerate(cat.syllabus)]
    return PathOut(nodes=nodes, edges=sorted(edges), route=route, projected=projected)


def progress(db: Session, user: User) -> ProgressOut:
    course = learner_svc.course_for(db, user)
    cat = learner_svc.load_catalogue(db, course.id)
    responses = list(db.scalars(select(Response).where(Response.user_id == user.id).order_by(Response.created_at, Response.id)))
    by_concept: dict[int, list[ProgressPoint]] = defaultdict(list)
    for r in responses:
        by_concept[r.concept_id].append(ProgressPoint(t=r.created_at.isoformat(), p=round(r.p_after, 4)))
    series = [ProgressSeries(concept_id=c, name=cat.names[c], points=by_concept[c]) for c in cat.syllabus if by_concept[c]]

    current = {c: cat.bkt(c).prior for c in cat.syllabus}
    daily: dict[date, tuple[float, int]] = {}
    count: dict[date, int] = defaultdict(int)
    for r in responses:
        d = r.created_at.astimezone(_tz()).date()
        current[r.concept_id] = r.p_after
        count[d] += 1
        daily[d] = (sum(current.values()) / len(current), count[d])
    return ProgressOut(series=series, daily=[DailyPoint(date=d.isoformat(), mean_mastery=round(v, 4), answers=n)
                                             for d, (v, n) in sorted(daily.items())])


def history(db: Session, user: User, limit: int = 50) -> list[HistoryItem]:
    uses = list(db.scalars(select(AidUse).where(AidUse.user_id == user.id).order_by(AidUse.id.desc()).limit(limit)))
    aids = {a.id: a for a in db.scalars(select(TeachingAid).where(TeachingAid.id.in_({u.aid_id for u in uses} or {0})))}
    names = {c.id: c.name for c in db.scalars(select(Concept).where(Concept.id.in_({u.concept_id for u in uses} or {0})))}
    return [HistoryItem(use_id=u.id, aid_id=u.aid_id, title=aids[u.aid_id].title, aid_type=aids[u.aid_id].aid_type.value,
                        concept_name=names.get(u.concept_id, ""), opened_at=u.opened_at.isoformat(),
                        completed=u.completed_at is not None, rating=u.rating, gain=u.gain,
                        check_status=u.check_status.value) for u in uses]
