"""Administrator views: users, jobs, the model report (offline research + live metrics), settings."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import AidUse, ModelRun, RecommendationItem, RecommendationList, ResearchReport, User
from app.models.base import Role
from app.services import settings as settings_svc


class AdminUser(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    is_synthetic: bool
    created_at: str
    last_active_at: str | None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    role: Role
    password: str = Field(min_length=8, max_length=128)


class RunOut(BaseModel):
    id: int
    kind: str
    status: str
    triggered_by: str
    run_date: str
    started_at: str
    finished_at: str | None
    metrics: dict
    notes: str
    has_artifact: bool


def users(db: Session, role: Role | None, q: str | None, include_synthetic: bool) -> list[AdminUser]:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if not include_synthetic:
        stmt = stmt.where(User.is_synthetic.is_(False))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))
    return [AdminUser(id=u.id, email=u.email, full_name=u.full_name, role=u.role, is_active=u.is_active,
                      is_synthetic=u.is_synthetic, created_at=u.created_at.isoformat(),
                      last_active_at=u.last_active_at.isoformat() if u.last_active_at else None)
            for u in db.scalars(stmt.order_by(User.role, User.full_name).limit(500))]


def create_user(db: Session, body: UserCreate) -> User:
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    u = User(email=email, full_name=body.full_name, role=body.role, password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    return u


def run_out(r: ModelRun) -> RunOut:
    return RunOut(id=r.id, kind=r.kind, status=r.status.value, triggered_by=r.triggered_by, run_date=r.run_date.isoformat(),
                  started_at=r.started_at.isoformat(), finished_at=r.finished_at.isoformat() if r.finished_at else None,
                  metrics=r.metrics or {}, notes=r.notes or "", has_artifact=r.artifact is not None)


def runs(db: Session, limit: int = 50) -> list[RunOut]:
    return [run_out(r) for r in db.scalars(select(ModelRun).order_by(ModelRun.id.desc()).limit(limit))]


def live_metrics(db: Session, include_synthetic: bool) -> dict:
    synthetic = {u for u in db.scalars(select(User.id).where(User.is_synthetic))}
    keep = (lambda uid: True) if include_synthetic else (lambda uid: uid not in synthetic)
    lists = [lst for lst in db.scalars(select(RecommendationList)) if keep(lst.user_id)]
    policy_of = {lst.id: lst.policy for lst in lists}
    phases: dict[str, int] = defaultdict(int)
    for lst in lists:
        phases[lst.phase] += 1
    per: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for it in db.scalars(select(RecommendationItem)):
        pol = policy_of.get(it.list_id)
        if pol is None:
            continue
        d = per[pol]
        d["items"] += 1
        d["impressions"] += it.impression_at is not None
        d["opened"] += it.opened_at is not None
        d["completed"] += it.completed_at is not None
        if it.gain is not None:
            d["checked"] += 1
            d["gain_sum"] += it.gain
            d["improved"] += it.gain > 0
    policies = {}
    for pol, d in per.items():
        policies[pol] = {
            "lists": sum(1 for lst in lists if lst.policy == pol),
            "items_shown": int(d["impressions"]),
            "ctr": round(d["opened"] / d["impressions"], 4) if d["impressions"] else None,
            "completion_rate": round(d["completed"] / d["opened"], 4) if d["opened"] else None,
            "checked": int(d["checked"]),
            "mean_gain": round(d["gain_sum"] / d["checked"], 4) if d["checked"] else None,
            "improved_share": round(d["improved"] / d["checked"], 4) if d["checked"] else None,
        }
    uses = [u for u in db.scalars(select(AidUse)) if keep(u.user_id)]
    gains = [u.gain for u in uses if u.gain is not None]
    return {
        "include_synthetic": include_synthetic,
        "students": len({u.user_id for u in uses}),
        "aid_uses": len(uses),
        "checked_uses": len(gains),
        "mean_gain": round(sum(gains) / len(gains), 4) if gains else None,
        "phases": dict(phases),
        "policies": policies,
    }


def model_report(db: Session, include_synthetic: bool) -> dict:
    latest: dict[str, RunOut] = {}
    for r in db.scalars(select(ModelRun).order_by(ModelRun.id.desc())):
        if r.kind not in latest and r.status.value in ("success", "skipped"):
            latest[r.kind] = run_out(r)
    weights, version = settings_svc.get(db, settings_svc.WEIGHTS)
    style, style_version = settings_svc.get(db, settings_svc.STYLE_UPDATE)
    return {
        "offline": {r.kind: r.payload for r in db.scalars(select(ResearchReport))},
        "live": live_metrics(db, include_synthetic),
        "latest_runs": {k: v.model_dump() for k, v in latest.items()},
        "config": {"weights": weights, "weights_version": version, "style_update": style,
                   "style_update_version": style_version},
    }
