"""Aid usage events: open, heartbeat, complete, rate, skip."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import AidUse, Interaction, RecommendationItem, TeachingAid, User
from app.models.base import CheckStatus, EventSource, EventType
from app.schemas.learning import EventIn, EventOut
from app.services import content as content_svc
from app.services import learner as learner_svc
from engine import clock


def _use(db: Session, user: User, body: EventIn) -> AidUse:
    if body.use_id:
        use = db.get(AidUse, body.use_id)
    else:
        use = db.scalars(select(AidUse).where(AidUse.user_id == user.id, AidUse.aid_id == body.aid_id)
                         .order_by(AidUse.id.desc())).first()
    if use is None or use.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Open the aid first.")
    return use


def record(db: Session, user: User, body: EventIn) -> EventOut:
    aid = db.get(TeachingAid, body.aid_id)
    if aid is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That teaching aid does not exist.")
    now = clock.now()
    item = None
    if body.item_id:
        item = db.get(RecommendationItem, body.item_id)
        if item is None or item.user_id != user.id or item.aid_id != aid.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That recommendation does not match this aid.")
    use: AidUse | None = None
    p_open = None

    if body.event == EventType.open:
        # Any earlier aid left without a quick check can no longer be measured.
        db.execute(update(AidUse).where(AidUse.user_id == user.id, AidUse.check_status == CheckStatus.pending)
                   .values(check_status=CheckStatus.no_check))
        db.execute(update(RecommendationItem).where(RecommendationItem.user_id == user.id,
                                                    RecommendationItem.check_status == CheckStatus.pending)
                   .values(check_status=CheckStatus.no_check))
        concept_id = content_svc.primary_concepts(db, [aid.id]).get(aid.id)
        course = learner_svc.course_for(db, user)
        cat = learner_svc.load_catalogue(db, course.id)
        p_open = learner_svc.mastery_map(db, user.id, cat).get(concept_id, 0.0) if concept_id else 0.0
        use = AidUse(user_id=user.id, aid_id=aid.id, concept_id=concept_id, rec_item_id=item.id if item else None,
                     source=EventSource.rec if item else body.source, opened_at=now, p_open=p_open,
                     check_status=CheckStatus.pending, persona=learner_svc.persona_of(db, user.id))
        db.add(use)
        if item is not None:
            item.opened_at = item.opened_at or now
            item.p_open = p_open
            item.check_status = CheckStatus.pending
        user.last_active_at = now
    elif body.event == EventType.heartbeat:
        use = _use(db, user, body)
        use.dwell_sec = min(use.dwell_sec + (body.seconds or 15), 6 * 3600)
    elif body.event == EventType.complete:
        use = _use(db, user, body)
        use.completed_at = use.completed_at or now
        if use.rec_item_id:
            ri = db.get(RecommendationItem, use.rec_item_id)
            if ri:
                ri.completed_at = ri.completed_at or now
    elif body.event == EventType.rate:
        if body.rating is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A rating from 1 to 5 is required.")
        use = _use(db, user, body)
        use.rating = body.rating
        if use.rec_item_id:
            ri = db.get(RecommendationItem, use.rec_item_id)
            if ri:
                ri.rating = body.rating
    elif body.event == EventType.skip:
        pass

    db.flush()
    db.add(Interaction(user_id=user.id, aid_id=aid.id, item_id=item.id if item else (use.rec_item_id if use else None),
                       event=body.event, source=body.source,
                       value={k: v for k, v in {"rating": body.rating, "seconds": body.seconds, "use_id": use.id if use else None}.items() if v is not None},
                       created_at=now))
    db.flush()
    return EventOut(use_id=use.id if use else None, p_open=round(p_open, 4) if p_open is not None else None)
