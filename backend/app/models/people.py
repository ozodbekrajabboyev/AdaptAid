from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import Arm, Role, created_at_col, str_enum


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(str_enum(Role), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Synthetic (simulated) learners created by `seed-demo`; excluded from every model fit.
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = created_at_col()
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    join_code: Mapped[str] = mapped_column(String(12), unique=True)
    created_at: Mapped[datetime] = created_at_col()

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="school_class", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"

    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    joined_at: Mapped[datetime] = created_at_col()
    # Pilot study: arm is assigned after the pre-test; form_order is "AB" or "BA".
    arm: Mapped[Arm | None] = mapped_column(str_enum(Arm))
    form_order: Mapped[str | None] = mapped_column(String(2))

    user: Mapped[User] = relationship(back_populates="enrollments")
    school_class: Mapped[SchoolClass] = relationship(back_populates="enrollments")
