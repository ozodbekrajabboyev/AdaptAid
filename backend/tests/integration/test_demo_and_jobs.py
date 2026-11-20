"""Integration: the demo seeder and the background jobs on committed data (mini content pack).

This module commits to the test database (jobs use their own connections and locks), so it
truncates every table when it finishes.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.content_pack import load_pack
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models import AidUse, LearnerFeatures, ModelRun, Response, User
from app.models.base import RiskLevel, RunStatus
from app.services import learner as learner_svc
from app.services import model_store
from app.services.seed import seed_pack
from tests.fixtures.minipack import make_minipack


@pytest.fixture(scope="module")
def demo(db_engine, tmp_path_factory):
    with SessionLocal() as db:
        seed_pack(db, load_pack(make_minipack(tmp_path_factory.mktemp("pack"))))
        db.commit()
    from app.demo import seed_demo

    result = seed_demo(n_students=24, days=28, seed=7, progress=lambda _: None)
    yield result
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    learner_svc._catalogue_cache.clear()
    model_store.clear_cache()


def login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": "demo-pass-2026"})
    assert r.status_code == 200, r.text


def test_demo_population(demo):
    assert demo["students"] == 24
    with SessionLocal() as db:
        days = {r.created_at.date() for r in db.scalars(select(Response))}
        assert len(days) >= 20  # realistic timestamps across the simulated weeks
        hero = db.scalar(select(User).where(User.email == "student@adaptaid.demo"))
        assert hero is not None and not hero.is_synthetic
        n_hero = db.scalar(select(func.count()).select_from(AidUse).where(AidUse.user_id == hero.id))
        # The mini pack has 3 concepts, so the hero runs out of material early; the
        # established-phase check for the real 13-concept course lives in scripts/demo_check.py.
        assert n_hero >= 10
        assert db.scalar(select(func.count()).select_from(AidUse).where(AidUse.gain.is_not(None))) > 100


def test_jobs_produced_models(demo):
    with SessionLocal() as db:
        personas = model_store.latest_run(db, "personas")
        assert personas is not None and personas.metrics["k"] >= 2 and "silhouette" in personas.metrics
        cf_model, run_id = model_store.latest_cf(db)
        assert cf_model is not None and run_id is not None
        flagged = list(db.scalars(select(LearnerFeatures).where(LearnerFeatures.risk_level != RiskLevel.low)))
        assert flagged and all(lf.risk_reasons for lf in flagged)
        assert db.scalar(select(func.count()).select_from(LearnerFeatures).where(LearnerFeatures.persona.is_not(None))) >= 20


def test_scheduled_job_runs_once_per_day(demo):
    from app.jobs.runner import run_job

    first = run_job("aid_stats", triggered_by="scheduler")
    second = run_job("aid_stats", triggered_by="scheduler")
    assert first is not None and second is None
    manual = run_job("aid_stats", triggered_by="admin", force=True)
    assert manual is not None
    with SessionLocal() as db:
        assert db.get(ModelRun, manual).status == RunStatus.success


def test_teacher_dashboards_have_data(demo):
    with TestClient(app) as client:
        login(client, "teacher@adaptaid.demo")
        klass = client.get("/api/classes/mine").json()[0]
        ov = client.get(f"/api/teacher/classes/{klass['id']}/overview").json()
        assert ov["kpis"]["n_students"] == 25 and ov["personas"]
        heat = client.get(f"/api/teacher/classes/{klass['id']}/heatmap").json()
        assert len(heat["values"]) == 25 and len(heat["values"][0]) == 3
        risky = client.get(f"/api/teacher/classes/{klass['id']}/at-risk").json()
        assert risky and risky[0]["reasons"]
        sugg = client.get(f"/api/teacher/classes/{klass['id']}/suggestions").json()
        assert isinstance(sugg, list)
        eff = client.get("/api/teacher/aid-effectiveness").json()
        assert any(r["n_checked"] > 0 for r in eff)
        sid = heat["students"][0]["id"]
        detail = client.get(f"/api/teacher/classes/{klass['id']}/students/{sid}").json()
        assert detail["summary"]["mastery"]
        # another teacher's class is off limits
        assert client.get(f"/api/teacher/classes/{klass['id'] + 999}/overview").status_code == 404


def test_hero_student_and_admin_report(demo):
    with TestClient(app) as client:
        login(client, "student@adaptaid.demo")
        s = client.get("/api/me/summary").json()
        assert s["phase"] in ("warm", "established") and s["style"]["n_updates"] >= 5
        rec = client.get("/api/recommendations/current").json()
        # Either aids with reasons, or (mini pack) the "mastered everything" message.
        assert (rec["items"] and all(i["explanation"] for i in rec["items"])) or rec["message"]
        client.post("/api/auth/logout")
        login(client, "admin@adaptaid.demo")
        report = client.get("/api/admin/model-report").json()
        assert report["live"]["policies"]["adaptive"]["ctr"] is not None
        assert {"personas", "cf", "aid_stats", "risk"} <= set(report["latest_runs"])
        assert client.get("/api/admin/users", params={"role": "teacher"}).json()[0]["email"] == "teacher@adaptaid.demo"
        assert client.get("/api/admin/jobs").json()
