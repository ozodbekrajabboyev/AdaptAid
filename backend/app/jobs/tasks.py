"""The background jobs. Each returns (metrics, artifact bytes or None).

Synthetic (simulated demo) learners are included unless the pilot study is active, so
the demo has data to learn from but pilot models are built from real learners only.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.jobs import features as feat
from app.models import AidStats, AidUse, Concept, LearnerFeatures, Response, User
from app.models.base import RiskLevel, Role
from app.services import learner as learner_svc
from app.services import settings as settings_svc
from engine import cf, clock
from engine.bkt import fit_brute_force, trace
from engine.profiling import personas, risk
from engine.signals import smoothed_mean

MIN_PERSONA_LEARNERS = 20
MIN_BKT_RESPONSES = 200
SMOOTHING_M = 5.0


def _include_synthetic(db: Session) -> bool:
    study, _ = settings_svc.get(db, settings_svc.STUDY)
    return not study.get("active", False)


def _student_ids(db: Session) -> set[int]:
    stmt = select(User.id).where(User.role == Role.student)
    if not _include_synthetic(db):
        stmt = stmt.where(User.is_synthetic.is_(False))
    return set(db.scalars(stmt))


def task_personas(db: Session) -> tuple[dict, bytes | None]:
    users = feat.students(db, _include_synthetic(db))
    now = clock.now()
    features = feat.compute(db, users, now)
    active = [u for u in users if features[u.id]["aid_uses"] >= 3]
    result = personas([features[u.id] for u in active]) if len(active) >= MIN_PERSONA_LEARNERS else None
    labels = dict(zip([u.id for u in active], result.labels, strict=True)) if result else {}
    for u in users:
        lf = db.get(LearnerFeatures, u.id) or LearnerFeatures(user_id=u.id)
        lf.persona = labels.get(u.id)
        lf.persona_label = result.names.get(labels[u.id]) if result and u.id in labels else None
        lf.features = features[u.id]
        lf.updated_at = now
        db.add(lf)
    db.flush()
    if result is None:
        return {"status": "not enough active learners", "active_learners": len(active),
                "needed": MIN_PERSONA_LEARNERS}, None
    counts: dict[str, int] = defaultdict(int)
    for lab in result.labels:
        counts[result.names[lab]] += 1
    return {"k": result.k, "silhouette": result.silhouette, "silhouette_by_k": result.silhouette_by_k,
            "stability_ari": result.stability_ari,
            "learners": len(active), "sizes": dict(counts), "centroids": result.centroids, "names": result.names}, None


def task_risk(db: Session) -> tuple[dict, bytes | None]:
    users = feat.students(db, include_synthetic=True)  # risk flags are shown for every student in a class
    now = clock.now()
    features = feat.compute(db, users, now)
    levels: dict[str, int] = defaultdict(int)
    for u in users:
        r = risk(features[u.id])
        lf = db.get(LearnerFeatures, u.id) or LearnerFeatures(user_id=u.id)
        lf.risk_score, lf.risk_level, lf.risk_reasons = r.score, RiskLevel(r.level), r.reasons
        lf.features = features[u.id]
        lf.updated_at = now
        db.add(lf)
        levels[r.level] += 1
    db.flush()
    return {"students": len(users), "levels": dict(levels)}, None


def task_aid_stats(db: Session) -> tuple[dict, bytes | None]:
    ids = _student_ids(db)
    uses = [u for u in db.scalars(select(AidUse)) if u.user_id in ids]
    persona = {lf.user_id: lf.persona for lf in db.scalars(select(LearnerFeatures)) if lf.persona}
    gains = [u.gain for u in uses if u.gain is not None]
    global_mean = sum(gains) / len(gains) if gains else 0.0
    groups: dict[tuple[int, str], list[AidUse]] = defaultdict(list)
    for u in uses:
        groups[(u.aid_id, "")].append(u)
        if u.user_id in persona:
            groups[(u.aid_id, persona[u.user_id])].append(u)
    db.execute(delete(AidStats))
    now = clock.now()
    for (aid_id, p), lst in groups.items():
        checked = [u.gain for u in lst if u.gain is not None]
        ratings = [u.rating for u in lst if u.rating is not None]
        db.add(AidStats(
            aid_id=aid_id, persona=p, n_uses=len(lst), n_completions=sum(1 for u in lst if u.completed_at),
            n_checked=len(checked), n_improved=sum(1 for g in checked if g > 0),
            mean_gain=round(sum(checked) / len(checked), 4) if checked else 0.0,
            smoothed_gain=round(smoothed_mean(sum(checked), len(checked), global_mean, SMOOTHING_M), 4),
            mean_rating=round(sum(ratings) / len(ratings), 3) if ratings else None, updated_at=now,
        ))
    db.flush()
    return {"aids": len({a for a, _ in groups}), "uses": len(uses), "checked": len(gains),
            "global_mean_gain": round(global_mean, 4)}, None


def task_cf(db: Session) -> tuple[dict, bytes | None]:
    ids = _student_ids(db)
    rows = [(u.user_id, u.aid_id, learner_svc.use_value(u)) for u in db.scalars(select(AidUse)) if u.user_id in ids]
    model = cf.train(rows)
    if model is None:
        return {"status": "not enough interactions", "rows": len(rows)}, None
    return {"kind": model.kind, "interactions": model.n_interactions, "users": model.n_users,
            "items": len(model.item_ids)}, cf.dumps(model)


def task_bkt(db: Session) -> tuple[dict, bytes | None]:
    study, _ = settings_svc.get(db, settings_svc.STUDY)
    if study.get("frozen"):
        return {"status": "skipped: BKT parameters are frozen for the pilot study"}, None
    ids = _student_ids(db)
    out = {}
    for concept in db.scalars(select(Concept)):
        seqs: dict[int, list[int]] = defaultdict(list)
        for r in db.scalars(select(Response).where(Response.concept_id == concept.id, Response.is_repeat.is_(False))
                            .order_by(Response.created_at, Response.id)):
            if r.user_id in ids:
                seqs[r.user_id].append(int(r.correct))
        n = sum(len(s) for s in seqs.values())
        if n < MIN_BKT_RESPONSES:
            out[concept.slug] = {"responses": n, "status": "not enough data"}
            continue
        fit = fit_brute_force(list(seqs.values()))
        p = fit.params
        concept.bkt_prior, concept.bkt_learn, concept.bkt_guess, concept.bkt_slip = p.prior, p.learn, p.guess, p.slip
        concept.params_version += 1
        concept.params_source = "fitted"
        # In-sample next-answer AUC as a sanity figure (the honest held-out AUC is in research/).
        preds, ys = [], []
        for s in seqs.values():
            pr, _ = trace(s, p)
            preds += pr
            ys += s
        out[concept.slug] = {"responses": n, "learners": len(seqs), **p.as_dict(), "auc_in_sample": _auc(ys, preds)}
    db.flush()
    return {"concepts": out}, None


def _auc(y: list[int], p: list[float]) -> float | None:
    if len(set(y)) < 2:
        return None
    from sklearn.metrics import roc_auc_score

    return round(float(roc_auc_score(y, p)), 4)


TASKS = {
    "personas": task_personas,
    "risk": task_risk,
    "aid_stats": task_aid_stats,
    "cf": task_cf,
    "bkt": task_bkt,
}
ORDER = ["personas", "risk", "aid_stats", "cf", "bkt"]
