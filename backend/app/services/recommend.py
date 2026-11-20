"""Recommendation lists as stored objects.

A list is generated on a state change (onboarding finished, quick check finished, manual
refresh) and stored with everything needed to analyse it later: policy, pilot arm, data
phase, weights/BKT versions, CF model run and each item's signals. Reading the current
list never regenerates it, so impressions and click-through rates stay meaningful.
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import AidStats, AidUse, Concept, RecommendationItem, RecommendationList, TeachingAid, User
from app.models.base import Arm, ListScope
from app.schemas.learning import FocusOut, RecAid, RecItemOut, RecListOut
from app.services import learner as learner_svc
from app.services import model_store
from app.services import settings as settings_svc
from engine import clock
from engine.explain import CONTROL_REASON, ExplainContext, PeerStat, contributions, explain
from engine.policy import AdaptivePolicy, StaticPolicy
from engine.style import dominant_pole


def _study_active(db: Session) -> bool:
    value, _ = settings_svc.get(db, settings_svc.STUDY)
    return bool(value.get("active"))


def generate(db: Session, user: User, reason: str, concept_id: int | None = None, k: int = 5) -> RecommendationList:
    course = learner_svc.course_for(db, user)
    cat = learner_svc.load_catalogue(db, course.id)
    view = learner_svc.build_view(db, user, cat)
    arm = learner_svc.arm_for(db, user)
    weights, thresholds, weights_version = settings_svc.weights(db)
    if arm == Arm.control:
        policy = StaticPolicy()
    else:
        policy = AdaptivePolicy(weights={p: dict(w) for p, w in weights.items()}, thresholds=thresholds)
    rec = policy.recommend(view, cat, k=k, concept=concept_id)
    _, model_run_id = model_store.latest_cf(db)
    bkt_version = max((c.params_version for c in db.scalars(select(Concept).where(Concept.course_id == course.id))), default=0)

    scope = ListScope.concept if concept_id else ListScope.home
    db.execute(
        update(RecommendationList)
        .where(RecommendationList.user_id == user.id, RecommendationList.scope == scope,
               RecommendationList.concept_id.is_(concept_id) if concept_id is None
               else RecommendationList.concept_id == concept_id,
               RecommendationList.is_current)
        .values(is_current=False)
    )
    lst = RecommendationList(
        user_id=user.id, scope=scope, concept_id=concept_id if concept_id else rec.focus_concept,
        policy=rec.policy, arm=arm.value, phase=rec.phase, weights_version=weights_version,
        bkt_params_version=bkt_version, model_run_id=model_run_id, reason=reason, is_current=True,
        created_at=clock.now(),
    )
    if scope == ListScope.home:
        lst.concept_id = rec.focus_concept
    db.add(lst)
    db.flush()

    persona = learner_svc.persona_of(db, user.id)
    peers: dict[int, PeerStat] = {}
    if persona:
        for s in db.scalars(select(AidStats).where(AidStats.persona == persona)):
            peers[s.aid_id] = PeerStat(s.n_checked, s.n_improved)
    pole = dominant_pole(view.style)
    ctx = ExplainContext(cat.names, view.mastery, dominant_pole=pole[1] if pole else None, peers=peers)
    contrib = contributions(rec.items, rec.weights) if rec.weights else [{} for _ in rec.items]
    for rank, (item, c) in enumerate(zip(rec.items, contrib, strict=True), start=1):
        text = CONTROL_REASON if arm == Arm.control else explain(item, c, ctx)
        db.add(RecommendationItem(
            list_id=lst.id, user_id=user.id, aid_id=item.aid.id, concept_id=item.concept_id, rank=rank,
            score=item.score, signals={k: v for k, v in item.parts.items()}, explanation=text,
            is_explore=item.is_explore,
        ))
    db.flush()
    return lst


def current(db: Session, user: User, concept_id: int | None = None) -> RecommendationList:
    scope = ListScope.concept if concept_id else ListScope.home
    stmt = select(RecommendationList).where(
        RecommendationList.user_id == user.id, RecommendationList.scope == scope, RecommendationList.is_current
    )
    if concept_id:
        stmt = stmt.where(RecommendationList.concept_id == concept_id)
    lst = db.scalars(stmt.order_by(RecommendationList.id.desc())).first()
    if lst is None:
        lst = generate(db, user, "initial", concept_id)
    return lst


def mark_impression(db: Session, user: User, list_id: int) -> int:
    res = db.execute(
        update(RecommendationItem)
        .where(RecommendationItem.list_id == list_id, RecommendationItem.user_id == user.id,
               RecommendationItem.impression_at.is_(None))
        .values(impression_at=clock.now())
    )
    return res.rowcount or 0


def to_out(db: Session, user: User, lst: RecommendationList) -> RecListOut:
    items = list(db.scalars(select(RecommendationItem).where(RecommendationItem.list_id == lst.id)
                            .order_by(RecommendationItem.rank)))
    aids = {a.id: a for a in db.scalars(select(TeachingAid).where(TeachingAid.id.in_([i.aid_id for i in items] or [0])))}
    course = learner_svc.course_for(db, user)
    cat = learner_svc.load_catalogue(db, course.id)
    mastery = learner_svc.mastery_map(db, user.id, cat)
    show_match = lst.arm != Arm.control.value and not _study_active(db)
    opened = {u.rec_item_id: u for u in db.scalars(select(AidUse).where(
        AidUse.rec_item_id.in_([i.id for i in items] or [0])))}
    out_items = []
    for i in items:
        a = aids[i.aid_id]
        use = opened.get(i.id)
        out_items.append(RecItemOut(
            id=i.id, rank=i.rank,
            aid=RecAid(id=a.id, title=a.title, description=a.description, aid_type=a.aid_type, source=a.source,
                       duration_min=a.duration_min, difficulty=a.difficulty),
            concept_id=i.concept_id, concept_name=cat.names.get(i.concept_id, ""),
            mastery=round(mastery.get(i.concept_id, 0.0), 4),
            match=round(i.score * 100) if show_match else None,
            explanation=i.explanation, is_explore=i.is_explore,
            opened=use is not None, completed=bool(use and use.completed_at),
        ))
    focus = None
    if lst.concept_id:
        n_aids = len(cat.aids_by_concept.get(lst.concept_id, []))
        focus = FocusOut(concept_id=lst.concept_id, name=cat.names.get(lst.concept_id, ""),
                         mastery=round(mastery.get(lst.concept_id, 0.0), 4), minutes=12 + 3 * min(n_aids, 2))
    message = None
    if not out_items:
        message = "You have mastered every concept in this course." if all(
            p >= 0.95 for p in mastery.values()) else "No teaching aids are available right now."
    return RecListOut(id=lst.id, scope=lst.scope, phase=lst.phase, focus=focus, items=out_items,
                      created_at=lst.created_at, message=message)
