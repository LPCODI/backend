"""Presentation project and slide preparation persistence models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin
from app.domain import DEFAULT_PRESENTATION_CONTEXT, PresentationContext, PresentationStatus

if TYPE_CHECKING:
    from app.models.evaluation import EvaluationPrioritySlide, QaQuestionSlide, RehearsalComparison
    from app.models.job import Job
    from app.models.rehearsal import Rehearsal, RehearsalSlideResult
    from app.models.user import User

JsonObject = dict[str, Any] | list[Any]
JSONB = JSON().with_variant(postgresql.JSONB, "postgresql")


class Presentation(TimestampMixin, SoftDeleteMixin, Base):
    """Presentation project centered on a professor-facing university project talk."""

    __tablename__ = "presentations"

    presentation_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    total_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    qa_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    presentation_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    presentation_context: Mapped[PresentationContext] = mapped_column(
        String(50),
        default=DEFAULT_PRESENTATION_CONTEXT,
        server_default=DEFAULT_PRESENTATION_CONTEXT.value,
        nullable=False,
    )
    status: Mapped[PresentationStatus] = mapped_column(
        String(40),
        default=PresentationStatus.DRAFT,
        server_default=PresentationStatus.DRAFT.value,
        nullable=False,
    )
    timing_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    script_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duplicated_from_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("presentations.presentation_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="presentations")
    duplicated_from: Mapped["Presentation | None"] = relationship(
        remote_side=[presentation_id],
        back_populates="duplicates",
    )
    duplicates: Mapped[list["Presentation"]] = relationship(back_populates="duplicated_from")
    files: Mapped[list["PresentationFile"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    slides: Mapped[list["Slide"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    analyses: Mapped[list["PresentationAnalysis"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    rehearsals: Mapped[list["Rehearsal"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    rehearsal_comparisons: Mapped[list["RehearsalComparison"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PresentationFile(SoftDeleteMixin, Base):
    """Uploaded presentation material and parsing state."""

    __tablename__ = "presentation_files"

    file_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    presentation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("presentations.presentation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    slide_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parse_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    presentation: Mapped["Presentation"] = relationship(back_populates="files")
    slides: Mapped[list["Slide"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Slide(TimestampMixin, Base):
    """Parsed slide text, image references, ordering, and exclusion state."""

    __tablename__ = "slides"
    __table_args__ = (
        UniqueConstraint("presentation_id", "sort_order", name="uq_slides_presentation_id_sort_order"),
    )

    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    presentation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("presentations.presentation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("presentation_files.file_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slide_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    presentation: Mapped["Presentation"] = relationship(back_populates="slides")
    file: Mapped["PresentationFile"] = relationship(back_populates="slides")
    analyses: Mapped[list["SlideAnalysis"]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    timings: Mapped[list["SlideTiming"]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    scripts: Mapped[list["SlideScript"]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    rehearsal_results: Mapped[list["RehearsalSlideResult"]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evaluation_priority_links: Mapped[list["EvaluationPrioritySlide"]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    qa_question_links: Mapped[list["QaQuestionSlide"]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PresentationAnalysis(Base):
    """Versioned whole-presentation AI analysis."""

    __tablename__ = "presentation_analyses"
    __table_args__ = (
        UniqueConstraint("presentation_id", "version", name="uq_presentation_analyses_presentation_id_version"),
    )

    presentation_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    presentation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("presentations.presentation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_core_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    weaknesses: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    professor_question_points: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    presentation: Mapped["Presentation"] = relationship(back_populates="analyses")
    slide_analyses: Mapped[list["SlideAnalysis"]] = relationship(
        back_populates="presentation_analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SlideAnalysis(Base):
    """Version-bound analysis for a single slide."""

    __tablename__ = "slide_analyses"

    slide_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    presentation_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("presentation_analyses.presentation_analysis_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("slides.slide_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    importance_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    complexity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    core_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_explanations: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    expected_questions: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    keywords: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    presentation_analysis: Mapped["PresentationAnalysis"] = relationship(back_populates="slide_analyses")
    slide: Mapped["Slide"] = relationship(back_populates="analyses")


class SlideTiming(TimestampMixin, Base):
    """Versioned slide timing allocation."""

    __tablename__ = "slide_timings"
    __table_args__ = (
        UniqueConstraint("slide_id", "version", name="uq_slide_timings_slide_id_version"),
    )

    slide_timing_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("slides.slide_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    transition_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    allocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    slide: Mapped["Slide"] = relationship(back_populates="timings")


class SlideScript(TimestampMixin, Base):
    """Versioned script text for a slide."""

    __tablename__ = "slide_scripts"
    __table_args__ = (
        UniqueConstraint("slide_id", "version", name="uq_slide_scripts_slide_id_version"),
    )

    slide_script_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("slides.slide_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    script_text: Mapped[str] = mapped_column(Text, nullable=False)
    core_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emphasis_words: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    transition_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    optional_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_questions: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    generation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    slide: Mapped["Slide"] = relationship(back_populates="scripts")
