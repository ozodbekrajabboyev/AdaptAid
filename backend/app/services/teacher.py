"""Teacher views: class overview, mastery heatmap, risk, personas, class aid suggestions, aid effectiveness."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AidStats,
    AidUse,
    Enrollment,
    LearnerFeatures,
    Mastery,
    SchoolClass,
    StyleProfile,
    TeachingAid,
    User,
)
from app.services import learner as learner_svc
from app.services import me as me_svc
from app.services import model_store
from engine import clock
from engine.explain import FORMAT_LABEL
from engine.group import StudentView, class_suggestions

BELOW = 0.6


class Kpis(BaseModel):
    n_students: int
    active_this_week: int
    avg_mastery: float
    aids_used_week: int
    avg_gain_week: float | None
    at_risk: int


class ConceptShare(BaseModel):
    concept_id: int
    name: str
    share_below: float  # unlocked for the student but below 60%: stuck
    share_locked: float  # prerequisites not reached yet
    mean_mastery: float


class PersonaCount(BaseModel):
    label: str
    count: int


class OverviewOut(BaseModel):
    class_id: int
    class_name: str
    course_title: str
    join_code: str
    kpis: Kpis
    concepts: list[ConceptShare]
    personas: list[PersonaCount]
    updated_at: str | None


class HeatStudent(BaseModel):
    id: int
    name: str
    risk_level: str
    persona: str | None
    synthetic: bool


class HeatmapOut(BaseModel):
    concepts: list[dict]
    students: list[HeatStudent]
    values: list[list[float]]


class RiskRow(BaseModel):
    id: int
    name: str
    level: str
    score: float
    reasons: list[str]
    last_active: str | None


class SuggestedAid(BaseModel):
    aid_id: int
    title: str
    aid_type: str
    format_label: str
    class_score: float
    share_poor_fit: float
    mean_gain: float | None
    n_checked: int


class AltGroupOut(BaseModel):
    aid_id: int
    title: str
    format_label: str
    students: list[str]


class SuggestionOut(BaseModel):
    concept_id: int
    concept_name: str
    share_below: float
    n_below: int
    n_students: int
    class_lean: str | None
    aids: list[SuggestedAid]
    alternatives: list[AltGroupOut]


class EffectivenessRow(BaseModel):
    aid_id: int
    title: str
    aid_type: str
    concept_name: str
    n_uses: int
    n_checked: int
    improved_share: float | None
    mean_gain: float | None
    smoothed_gain: float
    completion_rate: float | None
    mean_rating: float | None


def class_students(db: Session, class_id: int) -> list[User]:
    return list(db.scalars(select(User).join(Enrollment, Enrollment.user_id == User.id)
                           .where(Enrollment.class_id == class_id).order_by(User.full_name)))


def _mastery_matrix(db: Session, students: list[User], cat) -> dict[int, dict[int, float]]:
    ids = [s.id for s in students]
    rows: dict[int, dict[int, float]] = defaultdict(dict)
    for m in db.scalars(select(Mastery).where(Mastery.user_id.in_(ids or [0]))):
        rows[m.user_id][m.concept_id] = m.p_known
    return {s.id: {c: rows[s.id].get(c, cat.bkt(c).prior) for c in cat.syllabus} for s in students}


def overview(db: Session, klass: SchoolClass) -> OverviewOut:
    cat = learner_svc.load_catalogue(db, klass.course_id)
    students = class_students(db, klass.id)
    matrix = _mastery_matrix(db, students, cat)
    ids = [s.id for s in students]
    week = clock.now() - timedelta(days=7)
    uses = list(db.scalars(select(AidUse).where(AidUse.user_id.in_(ids or [0]), AidUse.opened_at >= week)))
    gains = [u.gain for u in uses if u.gain is not None]
    feats = {lf.user_id: lf for lf in db.scalars(select(LearnerFeatures).where(LearnerFeatures.user_id.in_(ids or [0])))}
    all_p = [p for row in matrix.values() for p in row.values()]
    from engine.bkt import UNLOCK

    def unlocked(sid: int, c: int) -> bool:
        return all(matrix[sid].get(p, 0.0) >= UNLOCK for p in cat.prereqs.get(c, set()))

    n = len(ids) or 1
    concepts = [
        ConceptShare(concept_id=c, name=cat.names[c],
                     share_below=round(sum(1 for s in ids if unlocked(s, c) and matrix[s][c] < BELOW) / n, 3),
                     share_locked=round(sum(1 for s in ids if not unlocked(s, c)) / n, 3),
                     mean_mastery=round(sum(matrix[s][c] for s in ids) / n, 4) if ids else 0.0)
        for c in cat.syllabus
    ]
    persona_counts = Counter(lf.persona_label for lf in feats.values() if lf.persona_label)
    updated = max((lf.updated_at for lf in feats.values()), default=None)
    from app.models import Course

    course = db.get(Course, klass.course_id)
    return OverviewOut(
        class_id=klass.id, class_name=klass.name, course_title=course.title if course else "", join_code=klass.join_code,
        kpis=Kpis(
            n_students=len(students), active_this_week=len({u.user_id for u in uses}),
            avg_mastery=round(sum(all_p) / len(all_p), 4) if all_p else 0.0, aids_used_week=len(uses),
            avg_gain_week=round(sum(gains) / len(gains), 4) if gains else None,
            at_risk=sum(1 for lf in feats.values() if lf.risk_level.value == "high"),
        ),
        concepts=concepts,
        personas=[PersonaCount(label=k, count=v) for k, v in persona_counts.most_common()],
        updated_at=updated.isoformat() if updated else None,
    )


def heatmap(db: Session, klass: SchoolClass) -> HeatmapOut:
    cat = learner_svc.load_catalogue(db, klass.course_id)
    students = class_students(db, klass.id)
    matrix = _mastery_matrix(db, students, cat)
    feats = {lf.user_id: lf for lf in db.scalars(select(LearnerFeatures).where(
        LearnerFeatures.user_id.in_([s.id for s in students] or [0])))}
    return HeatmapOut(
        concepts=[{"id": c, "name": cat.names[c]} for c in cat.syllabus],
        students=[HeatStudent(id=s.id, name=s.full_name,
                              risk_level=feats[s.id].risk_level.value if s.id in feats else "low",
                              persona=feats[s.id].persona_label if s.id in feats else None, synthetic=s.is_synthetic)
                  for s in students],
        values=[[round(matrix[s.id][c], 3) for c in cat.syllabus] for s in students],
    )


def at_risk(db: Session, klass: SchoolClass) -> list[RiskRow]:
    students = {s.id: s for s in class_students(db, klass.id)}
    rows = []
    for lf in db.scalars(select(LearnerFeatures).where(LearnerFeatures.user_id.in_(list(students) or [0]))):
        if lf.risk_level.value in ("medium", "high"):
            s = students[lf.user_id]
            rows.append(RiskRow(id=s.id, name=s.full_name, level=lf.risk_level.value, score=lf.risk_score,
                                reasons=list(lf.risk_reasons or []),
                                last_active=s.last_active_at.isoformat() if s.last_active_at else None))
    rows.sort(key=lambda r: -r.score)
    return rows


def suggestions(db: Session, klass: SchoolClass) -> list[SuggestionOut]:
    cat = learner_svc.load_catalogue(db, klass.course_id)
    students = class_students(db, klass.id)
    matrix = _mastery_matrix(db, students, cat)
    styles = {p.user_id: (p.ar, p.si, p.vv, p.sg) for p in db.scalars(select(StyleProfile).where(
        StyleProfile.user_id.in_([s.id for s in students] or [0])))}
    views = [StudentView(s.id, s.full_name, matrix[s.id], styles.get(s.id, (0.0, 0.0, 0.0, 0.0))) for s in students]
    stats = {s.aid_id: s for s in db.scalars(select(AidStats).where(AidStats.persona == ""))}
    out = class_suggestions(views, cat, {a: s.smoothed_gain for a, s in stats.items()})
    result = []
    for c in out:
        result.append(SuggestionOut(
            concept_id=c.concept_id, concept_name=c.concept_name, share_below=c.share_below, n_below=c.n_below,
            n_students=c.n_students, class_lean=c.class_lean,
            aids=[SuggestedAid(aid_id=a.aid.id, title=a.aid.title, aid_type=a.aid.aid_type,
                               format_label=FORMAT_LABEL.get(a.aid.aid_type, a.aid.aid_type), class_score=a.class_score,
                               share_poor_fit=a.share_poor_fit,
                               mean_gain=stats[a.aid.id].mean_gain if a.aid.id in stats and stats[a.aid.id].n_checked else None,
                               n_checked=stats[a.aid.id].n_checked if a.aid.id in stats else 0) for a in c.aids],
            alternatives=[AltGroupOut(aid_id=g.aid.id, title=g.aid.title,
                                      format_label=FORMAT_LABEL.get(g.aid.aid_type, g.aid.aid_type),
                                      students=[n for _, n in g.students]) for g in c.alternatives],
        ))
    return result


def student_detail(db: Session, klass: SchoolClass, student_id: int) -> dict:
    from fastapi import HTTPException, status

    if student_id not in {s.id for s in class_students(db, klass.id)}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That student is not in this class.")
    user = db.get(User, student_id)
    assert user is not None
    lf = db.get(LearnerFeatures, student_id)
    return {
        "id": user.id, "name": user.full_name, "email": user.email, "synthetic": user.is_synthetic,
        "summary": me_svc.summary(db, user).model_dump(),
        "history": [h.model_dump() for h in me_svc.history(db, user, limit=30)],
        "progress": me_svc.progress(db, user).model_dump(),
        "risk": {"level": lf.risk_level.value, "score": lf.risk_score, "reasons": lf.risk_reasons} if lf else None,
        "persona": lf.persona_label if lf else None,
        "features": lf.features if lf else {},
    }


def effectiveness(db: Session, course_id: int) -> list[EffectivenessRow]:
    cat = learner_svc.load_catalogue(db, course_id)
    stats = {s.aid_id: s for s in db.scalars(select(AidStats).where(AidStats.persona == ""))}
    aids = {a.id: a for a in db.scalars(select(TeachingAid).where(TeachingAid.course_id == course_id, TeachingAid.is_active))}
    rows = []
    for aid_id, a in aids.items():
        s = stats.get(aid_id)
        info = cat.aids.get(aid_id)
        rows.append(EffectivenessRow(
            aid_id=aid_id, title=a.title, aid_type=a.aid_type.value,
            concept_name=cat.names.get(info.concept_id, "") if info else "",
            n_uses=s.n_uses if s else 0, n_checked=s.n_checked if s else 0,
            improved_share=round(s.n_improved / s.n_checked, 3) if s and s.n_checked else None,
            mean_gain=s.mean_gain if s and s.n_checked else None, smoothed_gain=s.smoothed_gain if s else 0.0,
            completion_rate=round(s.n_completions / s.n_uses, 3) if s and s.n_uses else None,
            mean_rating=s.mean_rating if s else None,
        ))
    rows.sort(key=lambda r: (-r.smoothed_gain, -r.n_checked))
    return rows


def latest_personas_run(db: Session) -> dict | None:
    run = model_store.latest_run(db, "personas")
    return run.metrics if run else None
