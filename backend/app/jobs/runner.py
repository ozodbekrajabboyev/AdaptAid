"""Run jobs safely.

- A Postgres advisory lock, held on its own connection for the whole job, stops two
  processes running the same job at once (holding it on a pooled session connection
  would release it on the wrong connection after a commit).
- A scheduled job is skipped when a successful scheduled run already exists for today.
- Every run is recorded in model_runs (status, metrics, artifact, error).
"""

from __future__ import annotations

import logging
import threading
import traceback

from sqlalchemy import func, select

from app.core.db import SessionLocal, engine
from app.jobs.tasks import ORDER, TASKS
from app.models import ModelRun
from app.models.base import RunStatus
from app.services import model_store
from engine import clock

log = logging.getLogger("adaptaid.jobs")
LOCK_BASE = 72_000  # advisory lock ids: 72000 + index of the job


def run_job(kind: str, triggered_by: str = "scheduler", force: bool = False) -> int | None:
    """Run one job. Returns the model_runs id, or None when skipped."""
    if kind not in TASKS:
        raise ValueError(f"unknown job {kind!r}; choose from {sorted(TASKS)}")
    lock_id = LOCK_BASE + list(TASKS).index(kind)
    with engine.connect() as lock_conn:
        got = lock_conn.execute(select(func.pg_try_advisory_lock(lock_id))).scalar()
        lock_conn.commit()
        if not got:
            log.info("job %s is already running elsewhere; skipped", kind)
            return None
        try:
            return _run_locked(kind, triggered_by, force)
        finally:
            lock_conn.execute(select(func.pg_advisory_unlock(lock_id)))
            lock_conn.commit()


def _run_locked(kind: str, triggered_by: str, force: bool) -> int | None:
    today = clock.now().date()
    with SessionLocal() as db:
        if not force and triggered_by == "scheduler":
            done = db.scalar(select(ModelRun.id).where(ModelRun.kind == kind, ModelRun.run_date == today,
                                                       ModelRun.status == RunStatus.success,
                                                       ModelRun.triggered_by == "scheduler"))
            if done:
                return None
        run = ModelRun(kind=kind, run_date=today, status=RunStatus.running, triggered_by=triggered_by,
                       started_at=clock.now(), metrics={})
        db.add(run)
        db.commit()
        run_id = run.id
        try:
            metrics, artifact = TASKS[kind](db)
            run = db.get(ModelRun, run_id)
            assert run is not None
            run.metrics, run.artifact = metrics, artifact
            # Tasks report a top-level "status" when there was nothing to learn from yet.
            run.status = RunStatus.skipped if "status" in metrics else RunStatus.success
            run.finished_at = clock.now()
            db.commit()
        except Exception as e:  # recorded, never raised into the scheduler thread
            db.rollback()
            run = db.get(ModelRun, run_id)
            assert run is not None
            run.status = RunStatus.failed
            run.notes = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-2000:]}"
            run.finished_at = clock.now()
            db.commit()
            log.exception("job %s failed", kind)
    if kind == "cf":
        model_store.clear_cache()
    return run_id


def run_all(triggered_by: str = "scheduler", force: bool = False) -> dict[str, int | None]:
    return {kind: run_job(kind, triggered_by, force) for kind in ORDER}


def run_in_background(kind: str, triggered_by: str) -> threading.Thread:
    target = (lambda: run_all(triggered_by, force=True)) if kind == "all" else (
        lambda: run_job(kind, triggered_by, force=True))
    t = threading.Thread(target=target, name=f"job-{kind}", daemon=True)
    t.start()
    return t


def last_success_age_hours() -> float | None:
    with SessionLocal() as db:
        last = db.scalar(select(func.max(ModelRun.finished_at)).where(ModelRun.status == RunStatus.success))
    if last is None:
        return None
    return (clock.now() - last).total_seconds() / 3600
