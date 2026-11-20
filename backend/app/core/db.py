"""Database engine and session handling (synchronous SQLAlchemy).

Rules used across the app:
- Endpoints that touch the DB are plain ``def`` so FastAPI runs them in a threadpool.
- Services commit explicitly. ``get_db`` only rolls back on error and closes.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
