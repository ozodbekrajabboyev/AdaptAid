from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import (
    AttemptKind,
    CheckStatus,
    EventSource,
    EventType,
    ListScope,
    QuestionnaireSource,
    RiskLevel,
    created_at_col,
    str_enum,
)


class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[QuestionnaireSource] = mapped_column(str_enum(QuestionnaireSource))
    answers: Mapped[dict] = mapped_column(JSONB)
    vector: Mapped[list[float]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()


class StyleProfile(Base):
    """Learning-preference vector: starts from the questionnaire (prior), then learns from outcomes."""

    __tablename__ = "style_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ar: Mapped[float] = mapped_column(Float, default=0.0)
    si: Mapped[float] = mapped_column(Float, default=0.0)
    vv: Mapped[float] = mapped_column(Float, default=0.0)
    sg: Mapped[float] = mapped_column(Float, default=0.0)
    prior_ar: Mapped[float] = mapped_column(Float, default=0.0)
    prior_si: Mapped[float] = mapped_column(Float, default=0.0)
    prior_vv: Mapped[float] = mapped_column(Float, default=0.0)
    prior_sg: Mapped[float] = mapped_column(Float, default=0.0)
    n_updates: Mapped[int] = mapped_column(Integer, default=0)
    ema_gain: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = created_at_col()


class StyleUpdate(Base):
    __tablename__ = "style_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    aid_id: Mapped[int] = mapped_column(ForeignKey("teaching_aids.id", ondelete="CASCADE"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_items.id", ondelete="SET NULL"))
    gain: Mapped[float] = mapped_column(Float)
    baseline: Mapped[float] = mapped_column(Float)
    before: Mapped[list[float]] = mapped_column(JSONB)
    after: Mapped[list[float]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AttemptKind] = mapped_column(str_enum(AttemptKind), index=True)
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"))
    aid_id: Mapped[int | None] = mapped_column(ForeignKey("teaching_aids.id", ondelete="SET NULL"))
    rec_item_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_items.id", ondelete="SET NULL"))
    use_id: Mapped[int | None] = mapped_column(ForeignKey("aid_uses.id", ondelete="SET NULL"))
    question_ids: Mapped[list[int]] = mapped_column(JSONB)
    form: Mapped[str | None] = mapped_column(String(1))
    started_at: Mapped[datetime] = created_at_col()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    n_correct: Mapped[int] = mapped_column(Integer, default=0)
    n_total: Mapped[int] = mapped_column(Integer, default=0)


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    chosen_index: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool] = mapped_column(Boolean)
    # Item already seen by this learner: excluded from gain and from BKT refits.
    is_repeat: Mapped[bool] = mapped_column(Boolean, default=False)
    time_ms: Mapped[int | None] = mapped_column(Integer)
    p_before: Mapped[float] = mapped_column(Float)
    p_after: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = created_at_col()


class Mastery(Base):
    __tablename__ = "mastery"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    p_known: Mapped[float] = mapped_column(Float)
    n_answers: Mapped[int] = mapped_column(Integer, default=0)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = created_at_col()


class RecommendationList(Base):
    """One served list. Lists are regenerated on state changes, never as a side effect of a GET."""

    __tablename__ = "recommendation_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(str_enum(ListScope))
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"))
    policy: Mapped[str] = mapped_column(String(32))
    arm: Mapped[str | None] = mapped_column(String(16))
    phase: Mapped[str] = mapped_column(String(16))
    weights_version: Mapped[int] = mapped_column(Integer, default=0)
    bkt_params_version: Mapped[int] = mapped_column(Integer, default=0)
    model_run_id: Mapped[int | None] = mapped_column(ForeignKey("model_runs.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(32), default="manual")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = created_at_col()


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("recommendation_lists.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    aid_id: Mapped[int] = mapped_column(ForeignKey("teaching_aids.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    signals: Mapped[dict] = mapped_column(JSONB)
    explanation: Mapped[str] = mapped_column(Text)
    is_explore: Mapped[bool] = mapped_column(Boolean, default=False)
    impression_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Mastery when the aid was opened; gain is the residual of the following quick check.
    p_open: Mapped[float | None] = mapped_column(Float)
    gain: Mapped[float | None] = mapped_column(Float)
    check_status: Mapped[CheckStatus | None] = mapped_column(str_enum(CheckStatus))
    rating: Mapped[int | None] = mapped_column(Integer)


class AidUse(Base):
    """One use of a teaching aid by a learner: the unit every outcome statistic is built from.

    Created when the aid is opened (from a recommendation card, the library or the path).
    `p_open` is the learner's mastery at that moment; the quick check that follows gives
    the residual gain. Opening another aid before checking marks this one `no_check`.
    """

    __tablename__ = "aid_uses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    aid_id: Mapped[int] = mapped_column(ForeignKey("teaching_aids.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"))
    rec_item_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_items.id", ondelete="SET NULL"))
    source: Mapped[EventSource] = mapped_column(str_enum(EventSource), default=EventSource.direct)
    opened_at: Mapped[datetime] = created_at_col()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dwell_sec: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[int | None] = mapped_column(Integer)
    p_open: Mapped[float] = mapped_column(Float)
    check_status: Mapped[CheckStatus] = mapped_column(str_enum(CheckStatus), default=CheckStatus.pending)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gain: Mapped[float | None] = mapped_column(Float)
    persona: Mapped[str | None] = mapped_column(String(40))


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    aid_id: Mapped[int] = mapped_column(ForeignKey("teaching_aids.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_items.id", ondelete="SET NULL"))
    event: Mapped[EventType] = mapped_column(str_enum(EventType))
    source: Mapped[EventSource] = mapped_column(str_enum(EventSource), default=EventSource.direct)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created_at_col()


class AidStats(Base):
    """Aggregated aid outcomes, overall (persona='') and per learner persona."""

    __tablename__ = "aid_stats"

    aid_id: Mapped[int] = mapped_column(ForeignKey("teaching_aids.id", ondelete="CASCADE"), primary_key=True)
    persona: Mapped[str] = mapped_column(String(40), primary_key=True, default="")
    n_uses: Mapped[int] = mapped_column(Integer, default=0)
    n_completions: Mapped[int] = mapped_column(Integer, default=0)
    n_checked: Mapped[int] = mapped_column(Integer, default=0)
    n_improved: Mapped[int] = mapped_column(Integer, default=0)
    mean_gain: Mapped[float] = mapped_column(Float, default=0.0)
    smoothed_gain: Mapped[float] = mapped_column(Float, default=0.0)
    mean_rating: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = created_at_col()


class LearnerFeatures(Base):
    __tablename__ = "learner_features"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    persona: Mapped[str | None] = mapped_column(String(40))
    persona_label: Mapped[str | None] = mapped_column(String(80))
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[RiskLevel] = mapped_column(str_enum(RiskLevel), default=RiskLevel.low)
    risk_reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = created_at_col()
