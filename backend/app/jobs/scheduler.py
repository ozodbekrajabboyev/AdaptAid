"""Nightly scheduler (APScheduler), started from the FastAPI lifespan when SCHEDULER_ENABLED=true.

Run the API with a single worker (or enable the scheduler on exactly one process). On
start-up it catches up when the last successful run is more than 24 hours old, which
matters for laptops that sleep at night and hosts that idle.
"""

from __future__ import annotations

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.jobs.runner import last_success_age_hours, run_all

log = logging.getLogger("adaptaid.jobs")
_scheduler: BackgroundScheduler | None = None


def start() -> None:
    global _scheduler
    settings = get_settings()
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=settings.display_tz)
    _scheduler.add_job(run_all, CronTrigger(hour=settings.job_hour, minute=0), id="nightly", replace_existing=True,
                       max_instances=1, coalesce=True, misfire_grace_time=3600)
    _scheduler.start()
    log.info("scheduler started: nightly jobs at %02d:00 %s", settings.job_hour, settings.display_tz)

    def catch_up() -> None:
        age = last_success_age_hours()
        if age is None or age > 24:
            log.info("catching up on jobs (last success %s hours ago)", "never" if age is None else f"{age:.0f}")
            run_all("catch-up")

    threading.Thread(target=catch_up, name="jobs-catch-up", daemon=True).start()


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
