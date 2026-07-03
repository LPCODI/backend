"""Asynchronous background job persistence models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, String, Text, func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from sqlalchemy.types import TypeDecorator

from app.db import Base
from app.domain import JobStatus

if TYPE_CHECKING:
    from app.models.presentation import Presentation
    from app.models.rehearsal import Rehearsal
    from app.models.user import User

JsonObject = dict[str, Any] | list[Any]
JSONB = JSON().with_variant(postgresql.JSONB, "postgresql")


class JobUuid(TypeDecorator[UUID]):
    """Portable UUID type that keeps native PostgreSQL UUID DDL."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: UUID | str | None, dialect) -> UUID | str | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, UUID) else UUID(str(value))
        return str(value)

    def process_result_value(self, value: UUID | str | None, dialect) -> UUID | None:
        if value is None:
            return None
        return value if isinstance(value, UUID) else UUID(str(value))


class Job(Base):
    """Queued or running long-running task such as parsing, analysis, or reporting."""

    __tablename__ = "jobs"

    job_id: Mapped[UUID] = mapped_column(
        JobUuid(),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    presentation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("presentations.presentation_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rehearsal_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        String(30),
        default=JobStatus.PENDING,
        server_default=JobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_payload: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    result_payload: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="jobs")
    presentation: Mapped["Presentation | None"] = relationship(back_populates="jobs")
    rehearsal: Mapped["Rehearsal | None"] = relationship(back_populates="jobs")
    steps: Mapped[list["JobStep"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="JobStep.step_order",
    )


class JobStep(Base):
    """Progress and error state for one ordered stage inside a background job."""

    __tablename__ = "job_steps"

    job_step_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(
        JobUuid(),
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        String(30),
        default=JobStatus.PENDING,
        server_default=JobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="steps")
