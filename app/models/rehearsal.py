"""Rehearsal media, audio, pose, gaze, and slide result persistence models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base, SoftDeleteMixin, TimestampMixin
from app.domain import RehearsalStatus

if TYPE_CHECKING:
    from app.models.evaluation import (
        AgentEvaluation,
        FinalReport,
        QaAnswer,
        QaSession,
        RehearsalComparison,
    )
    from app.models.job import Job
    from app.models.presentation import Presentation, Slide

JsonObject = dict[str, Any] | list[Any]
JSONB = JSON().with_variant(postgresql.JSONB, "postgresql")


class Rehearsal(TimestampMixin, SoftDeleteMixin, Base):
    """One recorded practice attempt for a presentation project."""

    __tablename__ = "rehearsals"
    __table_args__ = (
        UniqueConstraint("presentation_id", "attempt_number", name="uq_rehearsals_presentation_id_attempt_number"),
        Index("ix_rehearsals_presentation_id_status", "presentation_id", "status"),
    )

    rehearsal_id: Mapped[int] = mapped_column(
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
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RehearsalStatus] = mapped_column(
        String(30),
        default=RehearsalStatus.CREATED,
        server_default=RehearsalStatus.CREATED.value,
        nullable=False,
        index=True,
    )
    total_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    presentation: Mapped["Presentation"] = relationship(back_populates="rehearsals")
    media: Mapped[list["RehearsalMedia"]] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audio_analysis: Mapped["AudioAnalysis | None"] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    pose_analysis: Mapped["PoseAnalysis | None"] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    gaze_analysis: Mapped["GazeAnalysis | None"] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    slide_results: Mapped[list["RehearsalSlideResult"]] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_evaluations: Mapped[list["AgentEvaluation"]] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    qa_sessions: Mapped[list["QaSession"]] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    final_reports: Mapped[list["FinalReport"]] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    base_comparisons: Mapped[list["RehearsalComparison"]] = relationship(
        foreign_keys="RehearsalComparison.base_rehearsal_id",
        back_populates="base_rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    target_comparisons: Mapped[list["RehearsalComparison"]] = relationship(
        foreign_keys="RehearsalComparison.target_rehearsal_id",
        back_populates="target_rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="rehearsal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RehearsalMedia(SoftDeleteMixin, Base):
    """Stored audio or video file metadata for a rehearsal."""

    __tablename__ = "rehearsal_media"
    __table_args__ = (
        UniqueConstraint("storage_bucket", "object_key", name="uq_rehearsal_media_storage_bucket_object_key"),
        Index("ix_rehearsal_media_rehearsal_id_media_type_status", "rehearsal_id", "media_type", "status"),
    )

    media_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="media")
    qa_answers: Mapped[list["QaAnswer"]] = relationship(back_populates="media")


class AudioAnalysis(TimestampMixin, Base):
    """Speech-to-text and delivery analysis summary for a rehearsal."""

    __tablename__ = "audio_analyses"

    audio_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    words_per_minute: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    filler_word_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    silence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    omission_summary: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    additional_content_summary: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="audio_analysis")
    filler_word_events: Mapped[list["FillerWordEvent"]] = relationship(
        back_populates="audio_analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    speech_events: Mapped[list["SpeechEvent"]] = relationship(
        back_populates="audio_analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FillerWordEvent(Base):
    """Single detected filler-word occurrence or grouped segment."""

    __tablename__ = "filler_word_events"
    __table_args__ = (
        Index(
            "ix_filler_word_events_audio_analysis_id_start_seconds",
            "audio_analysis_id",
            "start_seconds",
        ),
    )

    filler_word_event_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    audio_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("audio_analyses.audio_analysis_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filler_word: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    end_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    transcript_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    audio_analysis: Mapped["AudioAnalysis"] = relationship(back_populates="filler_word_events")


class SpeechEvent(Base):
    """Detected speech delivery event such as silence, repetition, or extra explanation."""

    __tablename__ = "speech_events"
    __table_args__ = (
        Index("ix_speech_events_audio_analysis_id_event_type", "audio_analysis_id", "event_type"),
    )

    speech_event_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    audio_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("audio_analyses.audio_analysis_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    end_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    transcript_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    details: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    audio_analysis: Mapped["AudioAnalysis"] = relationship(back_populates="speech_events")


class PoseAnalysis(TimestampMixin, Base):
    """Posture and repeated behavior analysis summary for a rehearsal video."""

    __tablename__ = "pose_analyses"

    pose_analysis_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    posture_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    stability_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    movement_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_metrics: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="pose_analysis")
    events: Mapped[list["PoseEvent"]] = relationship(
        back_populates="pose_analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PoseEvent(Base):
    """Detected posture or repeated behavior segment."""

    __tablename__ = "pose_events"
    __table_args__ = (
        Index("ix_pose_events_pose_analysis_id_event_type", "pose_analysis_id", "event_type"),
    )

    pose_event_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    pose_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pose_analyses.pose_analysis_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    end_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    details: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pose_analysis: Mapped["PoseAnalysis"] = relationship(back_populates="events")


class GazeAnalysis(TimestampMixin, Base):
    """Eye-line target distribution and gaze behavior summary."""

    __tablename__ = "gaze_analyses"

    gaze_analysis_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    professor_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    screen_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    floor_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    offscreen_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    dominant_target: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_metrics: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="gaze_analysis")
    events: Mapped[list["GazeEvent"]] = relationship(
        back_populates="gaze_analysis",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GazeEvent(Base):
    """Detected gaze segment such as long screen or floor fixation."""

    __tablename__ = "gaze_events"
    __table_args__ = (
        Index("ix_gaze_events_gaze_analysis_id_event_type", "gaze_analysis_id", "event_type"),
    )

    gaze_event_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True, nullable=False)
    gaze_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gaze_analyses.gaze_analysis_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    end_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    details: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    gaze_analysis: Mapped["GazeAnalysis"] = relationship(back_populates="events")


class RehearsalSlideResult(TimestampMixin, Base):
    """Planned versus actual timing and coverage for one slide in a rehearsal."""

    __tablename__ = "rehearsal_slide_results"
    __table_args__ = (
        UniqueConstraint("rehearsal_id", "slide_id", name="uq_rehearsal_slide_results_rehearsal_id_slide_id"),
    )

    rehearsal_slide_result_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    rehearsal_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("rehearsals.rehearsal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slide_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("slides.slide_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    planned_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    ended_at_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    coverage_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    omitted_keywords: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    extra_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    rehearsal: Mapped["Rehearsal"] = relationship(back_populates="slide_results")
    slide: Mapped["Slide"] = relationship(back_populates="rehearsal_results")
