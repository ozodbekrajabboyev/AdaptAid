from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content_pack import load_pack, validate
from app.models import Question, TeachingAid
from app.services.seed import seed_pack
from tests.conftest import register
from tests.fixtures.minipack import make_minipack


def test_minipack_is_valid(tmp_path):
    errors, _ = validate(load_pack(make_minipack(tmp_path)))
    assert errors == []


def test_seed_is_idempotent_and_archives_removed_items(db: Session, tmp_path):
    root = make_minipack(tmp_path)
    first = seed_pack(db, load_pack(root))
    assert (first.concepts, first.aids, first.questions) == (3, 15, 58)
    again = seed_pack(db, load_pack(root))
    assert again.deactivated_aids == 0
    assert db.scalar(select(func.count()).select_from(TeachingAid)) == 15

    # Remove one question from the pack: it is archived, not deleted.
    import json

    path = root / "concepts" / "alpha.json"
    data = json.loads(path.read_text())
    data["questions"] = [q for q in data["questions"] if q["key"] != "alpha-c10"]
    path.write_text(json.dumps(data))
    third = seed_pack(db, load_pack(root))
    assert third.deactivated_questions == 1
    q = db.scalar(select(Question).where(Question.key == "alpha-c10"))
    assert q is not None and not q.is_active


def test_students_can_browse_but_not_edit(client: TestClient, seeded):
    register(client, "s@example.com")
    concepts = client.get(f"/api/courses/{seeded.course_id}/concepts").json()
    assert [c["slug"] for c in concepts] == ["alpha", "beta", "gamma"]
    assert concepts[1]["prerequisites"] == [concepts[0]["id"]] and concepts[1]["is_study"]
    aids = client.get("/api/aids", params={"concept_id": concepts[0]["id"]}).json()
    assert len(aids) == 5 and aids[0]["aid_type"] == "notes"
    detail = client.get(f"/api/aids/{aids[4]['id']}").json()
    assert detail["aid_type"] == "practice" and detail["n_drill_questions"] == 5
    assert client.get("/api/questions").status_code == 403
    body = {"slug": "x-new", "title": "New aid", "description": "desc", "concept_id": concepts[0]["id"],
            "aid_type": "notes", "delivery": "native_md", "body_md": "text", "style_ar": 0, "style_si": 0,
            "style_vv": 0, "style_sg": 0}
    assert client.post("/api/aids", json=body).status_code == 403


def test_teacher_crud_and_validation(client: TestClient, seeded):
    register(client, "t@example.com", role="teacher")
    concepts = client.get(f"/api/courses/{seeded.course_id}/concepts").json()
    base = {"slug": "alpha-extra", "title": "Extra notes", "description": "More notes", "concept_id": concepts[0]["id"],
            "aid_type": "notes", "delivery": "native_md", "body_md": "Hello", "style_ar": -0.5, "style_si": 0,
            "style_vv": -0.8, "style_sg": 0.6}
    created = client.post("/api/aids", json=base)
    assert created.status_code == 201
    aid_id = created.json()["id"]
    assert client.post("/api/aids", json=base).status_code == 409  # duplicate slug
    bad = client.post("/api/aids", json={**base, "slug": "alpha-bad", "style_vv": 1.5})
    assert bad.status_code == 422
    nolink = client.post("/api/aids", json={**base, "slug": "alpha-link", "delivery": "external_url", "body_md": None})
    assert nolink.status_code == 422 and "link" in nolink.json()["detail"]
    http = client.post("/api/aids", json={**base, "slug": "alpha-http", "delivery": "external_url", "url": "http://x.org"})
    assert http.status_code == 422

    upd = client.put(f"/api/aids/{aid_id}", json={**base, "title": "Renamed", "concept_id": concepts[1]["id"]})
    assert upd.status_code == 200 and upd.json()["concept_name"] == "Beta"
    assert client.delete(f"/api/aids/{aid_id}").status_code == 204
    ids = [a["id"] for a in client.get("/api/aids").json()]
    assert aid_id not in ids  # archived aids are hidden from lists

    qs = client.get("/api/questions", params={"concept_id": concepts[1]["id"], "pool": "study"}).json()
    assert len(qs) == 10 and {q["form"] for q in qs} == {"A", "B"}
    newq = {"key": "alpha-c99", "concept_id": concepts[0]["id"], "stem": "What is 2 + 2?",
            "options": ["3", "4", "5", "22"], "correct_index": 1, "explanation": "Arithmetic.", "pool": "check"}
    assert client.post("/api/questions", json=newq).status_code == 201
    assert client.post("/api/questions", json={**newq, "key": "alpha-s99", "pool": "study"}).status_code == 422


def test_csv_round_trip(client: TestClient, seeded):
    register(client, "t2@example.com", role="teacher")
    exported = client.get("/api/content/export/aids.csv", params={"course_id": seeded.course_id})
    assert exported.status_code == 200
    assert exported.headers["content-disposition"].endswith('filename="aids.csv"')
    text = exported.text.replace("alpha notes", "alpha notes (edited)")
    res = client.post("/api/content/import/aids", params={"course_id": seeded.course_id},
                      files={"file": ("aids.csv", text.encode(), "text/csv")}).json()
    assert res == {"created": 0, "updated": 15, "errors": []}
    titles = {a["title"] for a in client.get("/api/aids").json()}
    assert "alpha notes (edited)" in titles

    qcsv = client.get("/api/content/export/questions.csv", params={"course_id": seeded.course_id}).text
    lines = qcsv.splitlines()
    r = client.post("/api/content/import/questions", params={"course_id": seeded.course_id},
                    files={"file": ("q.csv", qcsv.encode(), "text/csv")}).json()
    assert r["errors"] == [] and r["updated"] == 58
    bad_row = lines[0] + "\nzz-1,nope,check,,,stem,a,b,c,d,A,why,2\n"
    r2 = client.post("/api/content/import/questions", params={"course_id": seeded.course_id},
                     files={"file": ("q.csv", bad_row.encode(), "text/csv")}).json()
    assert r2["created"] == 0 and "unknown concept" in r2["errors"][0]
