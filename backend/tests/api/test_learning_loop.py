"""End-to-end tests of the adaptive learning loop through the HTTP API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AidUse,
    Enrollment,
    Mastery,
    Question,
    RecommendationList,
    Response,
    SchoolClass,
    StyleUpdate,
    User,
)
from app.models.base import Arm, CheckStatus, Role
from tests.conftest import register

ANSWERS_ALL_A = {f"q{n:02d}": "a" for n in range(1, 21)}


@pytest.fixture
def student(client: TestClient, db: Session, seeded):
    teacher = User(email="teach@example.com", password_hash=hash_password("x" * 10), full_name="T", role=Role.teacher)
    db.add(teacher)
    db.flush()
    klass = SchoolClass(course_id=seeded.course_id, teacher_id=teacher.id, name="CSE 3A", join_code="ABC234")
    db.add(klass)
    db.commit()
    return register(client, "learner@example.com", join_code="ABC234")


def correct_index(db: Session, qid: int) -> int:
    return db.get(Question, qid).correct_index


def do_quiz(client, db, attempt, right=True):
    for q in attempt["questions"]:
        ci = correct_index(db, q["id"])
        r = client.post(f"/api/quiz/attempts/{attempt['id']}/answer",
                        json={"question_id": q["id"], "chosen_index": ci if right else (ci + 1) % 4})
        assert r.status_code == 200, r.text
    return client.post(f"/api/quiz/attempts/{attempt['id']}/finish").json()


def onboard(client, db):
    assert client.get("/api/onboarding/status").json()["next_step"] == "questionnaire"
    q = client.get("/api/onboarding/questionnaire").json()
    assert len(q["items"]) == 20 and "a_pole" not in q["items"][0]  # scoring key is not exposed
    style = client.post("/api/onboarding/questionnaire", json={"answers": ANSWERS_ALL_A}).json()
    assert style["vector"] == style["prior"] and style["n_updates"] == 0
    assert client.get("/api/onboarding/status").json()["next_step"] == "diagnostic"
    diag = client.post("/api/quiz/start", json={"kind": "diagnostic"}).json()
    assert len(diag["questions"]) == 3  # one per concept
    fin = do_quiz(client, db, diag, right=False)
    assert fin["next_list_id"] is not None
    assert client.get("/api/onboarding/status").json()["next_step"] == "done"
    return fin


def test_full_learning_loop(client: TestClient, db: Session, student):
    onboard(client, db)

    # The current list is stable across reads (no regeneration on GET).
    first = client.get("/api/recommendations/current").json()
    again = client.get("/api/recommendations/current").json()
    assert first["id"] == again["id"]
    assert first["phase"] == "cold" and 1 <= len(first["items"]) <= 5
    assert first["focus"]["name"] == "Alpha"  # only the first concept is unlocked
    assert all(i["concept_name"] == "Alpha" for i in first["items"])
    assert sum(i["is_explore"] for i in first["items"]) <= 1
    assert all(i["explanation"] for i in first["items"]) and first["items"][0]["match"] is not None

    assert client.post("/api/recommendations/impression", json={"list_id": first["id"]}).status_code == 204

    item = first["items"][0]
    opened = client.post("/api/events", json={"aid_id": item["aid"]["id"], "event": "open", "item_id": item["id"]}).json()
    use_id = opened["use_id"]
    assert opened["p_open"] == pytest.approx(item["mastery"], abs=1e-4)
    assert client.post("/api/events", json={"aid_id": item["aid"]["id"], "event": "heartbeat", "use_id": use_id,
                                            "seconds": 30}).status_code == 200
    client.post("/api/events", json={"aid_id": item["aid"]["id"], "event": "complete", "use_id": use_id})
    client.post("/api/events", json={"aid_id": item["aid"]["id"], "event": "rate", "use_id": use_id, "rating": 5})

    check = client.post("/api/quiz/start", json={"kind": "check", "use_id": use_id}).json()
    assert len(check["questions"]) == 3 and all(q["concept_name"] == "Alpha" for q in check["questions"])
    before = db.scalar(select(Mastery.p_known).join(User).where(User.email == "learner@example.com",
                                                                 Mastery.concept_id == item["concept_id"]))
    fin = do_quiz(client, db, check, right=True)
    assert fin["passed"] is True and fin["gain"] is not None and fin["gain"] > 0
    assert fin["changes"][0]["after"] > fin["changes"][0]["before"]
    assert fin["changes"][0]["before"] == pytest.approx(before, abs=1e-4)

    use = db.get(AidUse, use_id)
    assert use.check_status == CheckStatus.done and use.dwell_sec == 30 and use.rating == 5 and use.completed_at
    assert db.scalar(select(func.count()).select_from(StyleUpdate)) == 1
    assert client.post("/api/quiz/start", json={"kind": "check", "use_id": use_id}).status_code == 409

    new_list = client.get("/api/recommendations/current").json()
    assert new_list["id"] == fin["next_list_id"] != first["id"]
    assert item["aid"]["id"] not in [i["aid"]["id"] for i in new_list["items"]]  # cooldown

    summary = client.get("/api/me/summary").json()
    assert summary["n_uses"] == 1 and summary["n_checks"] == 1 and summary["streak_days"] == 1
    assert summary["style"]["n_updates"] == 1 and summary["onboarding"]["next_step"] == "done"
    path = client.get("/api/me/path").json()
    assert path["route"] == [item["concept_id"]] and len(path["nodes"]) == 3
    assert {tuple(e) for e in path["edges"]} == {(path["nodes"][0]["id"], path["nodes"][1]["id"]),
                                                 (path["nodes"][1]["id"], path["nodes"][2]["id"])}
    prog = client.get("/api/me/progress").json()
    assert prog["series"] and prog["daily"][-1]["answers"] == 6
    hist = client.get("/api/me/history").json()
    assert hist[0]["gain"] == pytest.approx(fin["gain"])


def test_double_submit_is_idempotent(client: TestClient, db: Session, student):
    onboard(client, db)
    attempt = client.post("/api/quiz/start", json={"kind": "check", "concept_id": client.get("/api/me/summary").json()["mastery"][0]["concept_id"]}).json()
    q = attempt["questions"][0]
    body = {"question_id": q["id"], "chosen_index": correct_index(db, q["id"])}
    a = client.post(f"/api/quiz/attempts/{attempt['id']}/answer", json=body).json()
    b = client.post(f"/api/quiz/attempts/{attempt['id']}/answer", json=body).json()
    assert a == b
    assert db.scalar(select(func.count()).select_from(Response).where(Response.attempt_id == attempt["id"])) == 1
    m = db.scalar(select(Mastery).where(Mastery.concept_id == q["concept_id"]))
    assert m.p_known == pytest.approx(a["p_after"], abs=1e-4) and m.n_answers == 2  # 1 diagnostic + 1 check


def test_opening_another_aid_marks_previous_no_check(client: TestClient, db: Session, student):
    onboard(client, db)
    items = client.get("/api/recommendations/current").json()["items"]
    u1 = client.post("/api/events", json={"aid_id": items[0]["aid"]["id"], "event": "open", "item_id": items[0]["id"]}).json()["use_id"]
    client.post("/api/events", json={"aid_id": items[1]["aid"]["id"], "event": "open", "source": "library"})
    assert db.get(AidUse, u1).check_status == CheckStatus.no_check


def test_repeat_questions_are_excluded_from_gain(client: TestClient, db: Session, student):
    onboard(client, db)
    concept_id = client.get("/api/me/summary").json()["mastery"][0]["concept_id"]
    # Exhaust the 10-item check pool for this concept (4 checks x 3 = 12 > 10).
    for _ in range(3):
        do_quiz(client, db, client.post("/api/quiz/start", json={"kind": "check", "concept_id": concept_id}).json())
    aid_id = client.get("/api/aids", params={"concept_id": concept_id}).json()[0]["id"]
    use_id = client.post("/api/events", json={"aid_id": aid_id, "event": "open", "source": "library"}).json()["use_id"]
    check = client.post("/api/quiz/start", json={"kind": "check", "use_id": use_id}).json()
    fin = do_quiz(client, db, check)
    reps = db.scalars(select(Response.is_repeat).where(Response.attempt_id == check["id"])).all()
    assert reps.count(True) == 2 and reps.count(False) == 1  # one unseen item left, two repeats
    assert fin["gain"] is not None  # computed from the single fresh answer only


def test_control_arm_gets_course_plan_with_neutral_reason(client: TestClient, db: Session, student):
    onboard(client, db)
    e = db.scalar(select(Enrollment).join(User).where(User.email == "learner@example.com"))
    e.arm = Arm.control
    db.commit()
    lst = client.post("/api/recommendations/refresh", json={}).json()
    assert all(i["explanation"] == "Next in the course plan." for i in lst["items"])
    assert all(i["match"] is None for i in lst["items"])
    titles = [i["aid"]["title"] for i in lst["items"]]
    assert titles[0] == "alpha notes"  # teacher's default order: notes first
    row = db.get(RecommendationList, lst["id"])
    assert row.policy == "static" and row.arm == "control"


def test_students_cannot_see_others_attempts(client: TestClient, db: Session, student):
    onboard(client, db)
    attempt = client.post("/api/quiz/start", json={"kind": "diagnostic"}).json()
    client.cookies.clear()
    register(client, "other@example.com", join_code="ABC234")
    assert client.get(f"/api/quiz/attempts/{attempt['id']}").status_code == 404
    assert client.post(f"/api/quiz/attempts/{attempt['id']}/finish").status_code == 404


def test_ils_scores_and_validation(client: TestClient, student):
    ok = client.post("/api/onboarding/ils", json={"ar": [5, "reflective"], "si": [1, "sensing"], "vv": [9, "visual"],
                                                  "sg": [3, "global"]}).json()
    assert ok["dominant"] == "visual" and ok["vector"][2] == pytest.approx(9 / 11, abs=1e-3)
    bad = client.post("/api/onboarding/ils", json={"ar": [4, "active"], "si": [1, "sensing"], "vv": [1, "visual"],
                                                   "sg": [1, "global"]})
    assert bad.status_code == 422


def test_incomplete_questionnaire_is_rejected(client: TestClient, student):
    r = client.post("/api/onboarding/questionnaire", json={"answers": {"q01": "a"}})
    assert r.status_code == 422 and "19 left" in r.json()["detail"]


def test_teachers_cannot_use_student_endpoints(client: TestClient, seeded):
    register(client, "t9@example.com", role="teacher")
    assert client.get("/api/recommendations/current").status_code == 403
    assert client.post("/api/quiz/start", json={"kind": "diagnostic"}).status_code == 403
