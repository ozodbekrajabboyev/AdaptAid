"""Engagement features per learner, computed from aid sessions and quiz responses."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AidUse, Attempt, Concept, Response, TeachingAid, User
from app.models.base import AidType, AttemptKind, Role

VISUAL_THRESHOLD = 0.3
PRACTICE_TYPES = {AidType.practice, AidType.interactive}
TEXT_TYPES = {AidType.notes, AidType.article, AidType.cheat_sheet}


def students(db: Session, include_synthetic: bool) -> list[User]:
    stmt = select(User).where(User.role == Role.student, User.is_active)
    if not include_synthetic:
        stmt = stmt.where(User.is_synthetic.is_(False))
    return list(db.scalars(stmt))


def compute(db: Session, users: list[User], now: datetime, window_days: int = 28) -> dict[int, dict[str, float]]:
    ids = [u.id for u in users]
    if not ids:
        return {}
    since = now - timedelta(days=window_days)
    aids = {a.id: a for a in db.scalars(select(TeachingAid))}
    priors = {c.id: c.bkt_prior for c in db.scalars(select(Concept))}
    uses = defaultdict(list)
    for u in db.scalars(select(AidUse).where(AidUse.user_id.in_(ids))):
        uses[u.user_id].append(u)
    responses = defaultdict(list)
    for r in db.scalars(select(Response).where(Response.user_id.in_(ids)).order_by(Response.created_at, Response.id)):
        responses[r.user_id].append(r)
    check_attempts = {a.id for a in db.scalars(select(Attempt).where(Attempt.user_id.in_(ids), Attempt.kind == AttemptKind.check))}

    out: dict[int, dict[str, float]] = {}
    for user in users:
        us = [u for u in uses[user.id] if u.opened_at >= since]
        rs = responses[user.id]
        checks = [r for r in rs if r.attempt_id in check_attempts and r.created_at >= since]
        activity = [u.opened_at for u in uses[user.id]] + [r.created_at for r in rs]
        last = max(activity) if activity else user.created_at
        days = {t.date() for t in activity if t >= since}

        def mastery_at(cutoff: datetime, rs=rs) -> float:
            p = dict(priors)
            for r in rs:
                if r.created_at <= cutoff:
                    p[r.concept_id] = r.p_after
            return sum(p.values()) / len(p) if p else 0.0

        mean_now = mastery_at(now)
        mean_before = mastery_at(now - timedelta(days=14))
        n = len(us)
        types = [aids[u.aid_id].aid_type for u in us if u.aid_id in aids]
        gains = [u.gain for u in us if u.gain is not None]
        out[user.id] = {
            "active_days": float(len(days)),
            "aid_uses": float(n),
            "opens": float(n),
            "completion_rate": (sum(1 for u in us if u.completed_at) / n) if n else 0.0,
            "check_accuracy": (sum(r.correct for r in checks) / len(checks)) if checks else 0.0,
            "n_answers": float(len(checks)),
            # Residual gain: quick-check result minus what BKT expected at the learner's level.
            "mean_gain": round(sum(gains) / len(gains), 4) if gains else 0.0,
            "n_checked": float(len(gains)),
            "mean_mastery": round(mean_now, 4),
            "mastery_slope": round((mean_now - mean_before) / 14.0, 5),
            "days_since_active": round(max(0.0, (now - last).total_seconds() / 86400), 2),
            "share_visual": (sum(1 for u in us if u.aid_id in aids and aids[u.aid_id].style_vv > VISUAL_THRESHOLD) / n) if n else 0.0,
            "share_practice": (sum(1 for t in types if t in PRACTICE_TYPES) / n) if n else 0.0,
            "share_text": (sum(1 for t in types if t in TEXT_TYPES) / n) if n else 0.0,
        }
    return out
