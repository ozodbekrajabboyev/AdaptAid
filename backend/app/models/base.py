"""Shared column helpers and enums for the ORM models."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column


def str_enum(enum_cls: type[StrEnum], length: int = 24) -> SAEnum:
    """Store a StrEnum as VARCHAR holding its value (portable, easy to migrate)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Role(StrEnum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class Arm(StrEnum):
    adaptive = "adaptive"
    control = "control"


class AidType(StrEnum):
    video = "video"
    animation = "animation"
    interactive = "interactive"
    notes = "notes"
    worked_example = "worked_example"
    cheat_sheet = "cheat_sheet"
    concept_map = "concept_map"
    practice = "practice"
    article = "article"


class Delivery(StrEnum):
    native_md = "native_md"
    external_url = "external_url"
    interactive_component = "interactive_component"


class Interactivity(StrEnum):
    active = "active"
    expositive = "expositive"
    mixed = "mixed"


class QuestionPool(StrEnum):
    diagnostic = "diagnostic"
    check = "check"
    drill = "drill"
    study = "study"


class AttemptKind(StrEnum):
    diagnostic = "diagnostic"
    check = "check"
    drill = "drill"
    pretest = "pretest"
    posttest = "posttest"


class QuestionnaireSource(StrEnum):
    builtin = "builtin"
    ils = "ils"


class ListScope(StrEnum):
    home = "home"
    concept = "concept"


class CheckStatus(StrEnum):
    pending = "pending"
    done = "done"
    no_check = "no_check"


class EventType(StrEnum):
    open = "open"
    heartbeat = "heartbeat"
    complete = "complete"
    rate = "rate"
    skip = "skip"


class EventSource(StrEnum):
    rec = "rec"
    library = "library"
    path = "path"
    direct = "direct"


class RunStatus(StrEnum):
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class SurveyKind(StrEnum):
    sus = "sus"
    satisfaction = "satisfaction"
