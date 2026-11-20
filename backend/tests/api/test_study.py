"""Pilot study: consent, counterbalanced forms, stratified arm assignment, post-test, SUS, export, freeze."""

from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.jobs.tasks import task_bkt
from app.models import Enrollment, Question, SchoolClass, User
from app.models.base import Role
from app.services import settings as settings_svc
from app.services.study import sus_score
from tests.conftest import register


@pytest.fixture
def study_class(db: Session, seeded):
    teacher = User(email="pi@example.com", password_hash=hash_password("x" * 10), full_name="PI", role=Role.teacher)
    db.add(teacher)
    db.flush()
    db.add(SchoolClass(course_id=seeded.course_id, teacher_id=teacher.id, name="Pilot", join_code="PILOT2"))
    value, _ = settings_svc.get(db, settings_svc.STUDY)
    settings_svc.put(db, settings_svc.STUDY, {**value, "active": True})
    db.commit()
    return "PILOT2"


def take_pretest(client: TestClient, db: Session, n_right: int):
    attempt = client.post("/api/quiz/start", json={"kind": "pretest"}).json()
    for i, q in enumerate(attempt["questions"]):
        ci = db.get(Question, q["id"]).correct_index
        client.post(f"/api/quiz/attempts/{attempt['id']}/answer",
                    json={"question_id": q["id"], "chosen_index": ci if i < n_right else (ci + 1) % 4})
    return client.post(f"/api/quiz/attempts/{attempt['id']}/finish").json(), attempt


def test_sus_scoring():
    assert sus_score([3] * 10) == 50.0
    assert sus_score([5, 1] * 5) == 100.0
    assert sus_score([1, 5] * 5) == 0.0
    with pytest.raises(ValueError):
        sus_score([3] * 9)


def test_consent_pretest_then_arm(client: TestClient, db: Session, study_class):
    register(client, "p1@example.com", join_code=study_class)
    st = client.get("/api/onboarding/status").json()
    assert st["next_step"] == "consent" and "research project" in st["consent_text"]
    assert client.post("/api/onboarding/consent").status_code == 204
    e = db.scalar(select(Enrollment).join(User).where(User.email == "p1@example.com"))
    assert e.form_order in ("AB", "BA") and e.arm is None
    assert client.get("/api/onboarding/status").json()["next_step"] == "pretest"
    fin, attempt = take_pretest(client, db, n_right=3)
    forms = {db.get(Question, q["id"]).form for q in attempt["questions"]}
    assert forms == {e.form_order[0]} and len(attempt["questions"]) == 5
    db.refresh(e)
    assert e.arm is not None
    # The pilot still runs the full diagnostic after the questionnaire.
    assert client.get("/api/onboarding/status").json()["next_step"] == "questionnaire"


def test_stratified_assignment_is_balanced(client: TestClient, db: Session, study_class):
    for i in range(18):
        client.cookies.clear()
        register(client, f"s{i}@example.com", join_code=study_class)
        client.post("/api/onboarding/consent")
        take_pretest(client, db, n_right=[0, 3, 5][i % 3])  # three score bands, six students each
    arms = Counter(e.arm.value for e in db.scalars(select(Enrollment).where(Enrollment.arm.is_not(None))))
    assert arms["adaptive"] == arms["control"] == 9
    orders = Counter(e.form_order for e in db.scalars(select(Enrollment)))
    assert abs(orders["AB"] - orders["BA"]) <= 1  # counterbalanced forms


def test_posttest_survey_and_export(client: TestClient, db: Session, study_class):
    register(client, "p2@example.com", join_code=study_class)
    client.post("/api/onboarding/consent")
    take_pretest(client, db, n_right=2)
    assert client.post("/api/study/posttest").status_code == 409  # not open yet
    value, _ = settings_svc.get(db, settings_svc.STUDY)
    settings_svc.put(db, settings_svc.STUDY, {**value, "posttest_open": True})
    db.commit()
    assert client.get("/api/study/status").json()["posttest_open"] is True
    post = client.post("/api/study/posttest").json()
    e = db.scalar(select(Enrollment).join(User).where(User.email == "p2@example.com"))
    assert {db.get(Question, q["id"]).form for q in post["questions"]} == {e.form_order[1]}  # the other form
    for q in post["questions"]:
        client.post(f"/api/quiz/attempts/{post['id']}/answer",
                    json={"question_id": q["id"], "chosen_index": db.get(Question, q["id"]).correct_index})
    client.post(f"/api/quiz/attempts/{post['id']}/finish")
    assert client.post("/api/study/posttest").status_code == 409  # only once
    r = client.post("/api/study/survey", json={"sus": [4, 2] * 5, "satisfaction": [4, 4, 5, 3, 4], "comment": "ok"})
    assert r.status_code == 201 and r.json()["sus"] == 75.0
    assert client.post("/api/study/survey", json={"sus": [4, 2] * 5, "satisfaction": [4] * 5}).status_code == 409

    client.cookies.clear()
    db.add(User(email="adm@example.com", password_hash=hash_password("admin-pass-1"), full_name="A", role=Role.admin))
    db.commit()
    client.post("/api/auth/login", json={"email": "adm@example.com", "password": "admin-pass-1"})
    csv_text = client.get("/api/admin/study/export.csv").text
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("participant,class,arm")
    assert "p2@example.com" not in csv_text and lines[1].startswith("P001,Pilot,")
    row = dict(zip(lines[0].split(","), lines[1].split(","), strict=True))
    assert float(row["pre_score"]) == pytest.approx(0.4) and float(row["post_score"]) == 1.0
    assert float(row["normalized_gain"]) == pytest.approx(1.0) and float(row["sus"]) == 75.0


def test_frozen_parameters_skip_bkt_refit(db: Session, seeded):
    value, _ = settings_svc.get(db, settings_svc.STUDY)
    settings_svc.put(db, settings_svc.STUDY, {**value, "frozen": True})
    metrics, artifact = task_bkt(db)
    assert "frozen" in metrics["status"] and artifact is None
