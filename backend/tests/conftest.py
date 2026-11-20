"""Test setup.

- Tests use the `adaptaid_test` database (override with TEST_DATABASE_URL).
- The schema is rebuilt once per session by running the real Alembic migrations.
- Each test runs inside an outer transaction; service commits become savepoints and
  everything is rolled back afterwards, so tests are isolated and fast.
"""

import os

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://adaptaid:adaptaid@localhost:5434/adaptaid_test"
)
os.environ["DATABASE_URL"] = TEST_DB
os.environ["APP_ENV"] = "test"
os.environ["TEACHER_INVITE_CODE"] = "TEACH-TEST"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def db_engine():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = TEST_DB
    command.upgrade(cfg, "head")
    yield engine


@pytest.fixture
def db(db_engine) -> Iterator[Session]:
    conn = db_engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def register(client: TestClient, email: str, role: str = "student", **extra) -> dict:
    body = {"email": email, "password": "correct-horse-1", "full_name": "Test Person", "role": role, **extra}
    if role == "teacher":
        body.setdefault("invite_code", "TEACH-TEST")
    res = client.post("/api/auth/register", json=body)
    assert res.status_code == 201, res.text
    return res.json()
