from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Course, User
from app.models.base import Role
from tests.conftest import register


def test_register_sets_session_cookie_and_me_works(client: TestClient):
    user = register(client, "Asha@Example.com")
    assert user["email"] == "asha@example.com"
    assert user["role"] == "student"
    assert "adaptaid_session" in client.cookies
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


def test_session_cookie_is_httponly_and_lax(client: TestClient):
    res = client.post(
        "/api/auth/register",
        json={"email": "c@example.com", "password": "correct-horse-1", "full_name": "C D"},
    )
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "secure" not in cookie  # COOKIE_SECURE=false in tests (plain http)


def test_duplicate_email_is_rejected(client: TestClient):
    register(client, "dup@example.com")
    res = client.post(
        "/api/auth/register",
        json={"email": "DUP@example.com", "password": "correct-horse-1", "full_name": "Dup"},
    )
    assert res.status_code == 409


def test_teacher_needs_invite_code(client: TestClient):
    res = client.post(
        "/api/auth/register",
        json={"email": "t@example.com", "password": "correct-horse-1", "full_name": "T", "role": "teacher"},
    )
    assert res.status_code == 422 or res.status_code == 403
    ok = register(client, "t2@example.com", role="teacher")
    assert ok["role"] == "teacher"


def test_cannot_self_register_as_admin(client: TestClient):
    res = client.post(
        "/api/auth/register",
        json={"email": "x@example.com", "password": "correct-horse-1", "full_name": "X", "role": "admin"},
    )
    assert res.status_code == 422


def test_login_logout_flow(client: TestClient, db: Session):
    db.add(User(email="l@example.com", password_hash=hash_password("pw-12345678"), full_name="L", role=Role.student))
    db.commit()
    bad = client.post("/api/auth/login", json={"email": "l@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    good = client.post("/api/auth/login", json={"email": "L@example.com", "password": "pw-12345678"})
    assert good.status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    out = client.post("/api/auth/logout")
    assert out.status_code == 204
    assert "adaptaid_session" not in client.cookies
    assert client.get("/api/auth/me").status_code == 401


def test_bearer_token_also_works(client: TestClient):
    register(client, "b@example.com")
    token = client.cookies.get("adaptaid_session")
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_garbage_token_is_401(client: TestClient):
    client.cookies.set("adaptaid_session", "not-a-jwt")
    assert client.get("/api/auth/me").status_code == 401


def test_role_guards_on_classes(client: TestClient, db: Session):
    course = Course(code="DSA", title="Data Structures")
    db.add(course)
    db.commit()

    register(client, "teacher@example.com", role="teacher")
    created = client.post("/api/classes", json={"name": "CSE 3A", "course_id": course.id})
    assert created.status_code == 201
    code = created.json()["join_code"]
    assert len(code) == 6

    # A teacher cannot join a class as a student.
    assert client.post("/api/classes/join", json={"code": code}).status_code == 403

    client.cookies.clear()
    register(client, "student@example.com")
    # A student cannot create a class.
    assert client.post("/api/classes", json={"name": "Nope", "course_id": course.id}).status_code == 403
    joined = client.post("/api/classes/join", json={"code": code.lower()})
    assert joined.status_code == 200
    assert joined.json()["n_students"] == 1
    mine = client.get("/api/classes/mine").json()
    assert [k["join_code"] for k in mine] == [code]
    assert client.post("/api/classes/join", json={"code": "ZZZZZZ"}).status_code == 404


def test_register_with_join_code(client: TestClient, db: Session):
    course = Course(code="DSA2", title="DS")
    db.add(course)
    db.commit()
    register(client, "teach2@example.com", role="teacher")
    res = client.post("/api/classes", json={"name": "Batch B", "course_id": course.id})
    assert res.status_code == 201, res.text
    code = res.json()["join_code"]
    client.cookies.clear()
    register(client, "kid@example.com", join_code=code)
    assert len(client.get("/api/classes/mine").json()) == 1
