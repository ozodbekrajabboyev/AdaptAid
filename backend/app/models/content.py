from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import AidType, Delivery, Interactivity, QuestionPool, created_at_col, str_enum


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created_at_col()

    concepts: Mapped[list["Concept"]] = relationship(back_populates="course", order_by="Concept.order_index")


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("course_id", "slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    # Syllabus order: the "static instruction" sequence used by the control policy.
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    # Bayesian Knowledge Tracing parameters for this concept.
    bkt_prior: Mapped[float] = mapped_column(Float, default=0.2)
    bkt_learn: Mapped[float] = mapped_column(Float, default=0.15)
    bkt_guess: Mapped[float] = mapped_column(Float, default=0.2)
    bkt_slip: Mapped[float] = mapped_column(Float, default=0.1)
    params_version: Mapped[int] = mapped_column(Integer, default=0)
    params_source: Mapped[str] = mapped_column(String(32), default="default")
    # Concepts covered by the pilot study's pre/post tests.
    is_study: Mapped[bool] = mapped_column(Boolean, default=False)

    course: Mapped[Course] = relationship(back_populates="concepts")


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"
    __table_args__ = (CheckConstraint("concept_id <> prereq_id", name="no_self_prereq"),)

    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    prereq_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)


class TeachingAid(Base):
    __tablename__ = "teaching_aids"
    __table_args__ = (
        UniqueConstraint("course_id", "slug"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(96))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    aid_type: Mapped[AidType] = mapped_column(str_enum(AidType), index=True)
    delivery: Mapped[Delivery] = mapped_column(str_enum(Delivery))
    url: Mapped[str | None] = mapped_column(String(500))
    body_md: Mapped[str | None] = mapped_column(Text)
    component_key: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(120), default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    # Felder–Silverman style vector, each in [-1, 1]:
    # +active/-reflective, +sensing/-intuitive, +visual/-verbal, +sequential/-global
    style_ar: Mapped[float] = mapped_column(Float, default=0.0)
    style_si: Mapped[float] = mapped_column(Float, default=0.0)
    style_vv: Mapped[float] = mapped_column(Float, default=0.0)
    style_sg: Mapped[float] = mapped_column(Float, default=0.0)
    interactivity: Mapped[Interactivity] = mapped_column(str_enum(Interactivity), default=Interactivity.expositive)
    duration_min: Mapped[int] = mapped_column(Integer, default=10)
    language: Mapped[str] = mapped_column(String(8), default="en")
    # Teacher's default order within a concept (used by the static/control policy).
    default_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    concept_links: Mapped[list["AidConcept"]] = relationship(back_populates="aid", cascade="all, delete-orphan")


class AidConcept(Base):
    __tablename__ = "aid_concepts"

    aid_id: Mapped[int] = mapped_column(ForeignKey("teaching_aids.id", ondelete="CASCADE"), primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    aid: Mapped[TeachingAid] = relationship(back_populates="concept_links")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("course_id", "key"),
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="question_difficulty_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSONB)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    pool: Mapped[QuestionPool] = mapped_column(str_enum(QuestionPool), index=True)
    # Pilot study parallel forms: "A" or "B" (pool=study only).
    form: Mapped[str | None] = mapped_column(String(1))
    # Drill items belong to a practice aid.
    aid_id: Mapped[int | None] = mapped_column(ForeignKey("teaching_aids.id", ondelete="SET NULL"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
