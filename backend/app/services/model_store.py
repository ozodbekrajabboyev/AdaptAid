"""Model artifacts live in Postgres (model_runs.artifact). Each process caches the latest one."""

from __future__ import annotations

import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelRun
from app.models.base import RunStatus
from engine import cf

_lock = threading.Lock()
_cache: dict[str, tuple[int | None, object | None]] = {}


def latest_run(db: Session, kind: str) -> ModelRun | None:
    return db.scalars(
        select(ModelRun).where(ModelRun.kind == kind, ModelRun.status == RunStatus.success)
        .order_by(ModelRun.id.desc()).limit(1)
    ).first()


def latest_cf(db: Session) -> tuple[cf.CFModel | None, int | None]:
    run_id = db.scalar(
        select(ModelRun.id).where(ModelRun.kind == "cf", ModelRun.status == RunStatus.success,
                                  ModelRun.artifact.is_not(None))
        .order_by(ModelRun.id.desc()).limit(1)
    )
    with _lock:
        cached_id, model = _cache.get("cf", (None, None))
        if run_id == cached_id:
            return model, run_id  # type: ignore[return-value]
    if run_id is None:
        return None, None
    data = db.scalar(select(ModelRun.artifact).where(ModelRun.id == run_id))
    model = cf.loads(data) if data else None
    with _lock:
        _cache["cf"] = (run_id, model)
    return model, run_id


def clear_cache() -> None:
    with _lock:
        _cache.clear()
