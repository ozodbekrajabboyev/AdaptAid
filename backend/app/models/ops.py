from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import RunStatus, SurveyKind, created_at_col, str_enum


class ModelRun(Base):
    """One run of a background job. Small model artifacts are stored inline (bytea)."""

    __tablename__ = "model_runs"
    __table_args__ = (
        # At most one successful run per job kind per day (jobs skip if one exists).
        Index("uq_model_runs_success_per_day", "kind", "run_date", unique=True,
              postgresql_where=text("status = 'success'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    run_date: Mapped[date] = mapped_column(Date)
    status: Mapped[RunStatus] = mapped_column(str_enum(RunStatus))
    triggered_by: Mapped[str] = mapped_column(String(32), default="scheduler")
    started_at: Mapped[datetime] = created_at_col()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    artifact: Mapped[bytes | None] = mapped_column(LargeBinary)
    notes: Mapped[str] = mapped_column(Text, default="")


class ResearchReport(Base):
    """Offline evaluation results imported from research/outputs/*.json."""

    __tablename__ = "research_reports"

    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    imported_at: Mapped[datetime] = created_at_col()


class Setting(Base):
    """Versioned key/value settings (recommender weights, study config, ...)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = created_at_col()


class Consent(Base):
    __tablename__ = "consents"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[str] = mapped_column(String(16))
    consented_at: Mapped[datetime] = created_at_col()


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[SurveyKind] = mapped_column(str_enum(SurveyKind))
    answers: Mapped[dict] = mapped_column(JSONB)
    score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = created_at_col()
