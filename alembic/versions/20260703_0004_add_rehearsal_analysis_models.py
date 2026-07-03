"""Add rehearsal analysis tables.

Revision ID: 20260703_0004
Revises: 20260703_0003
Create Date: 2026-07-03 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0004"
down_revision: str | None = "20260703_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create rehearsal, media, audio, pose, gaze, and slide result tables."""

    op.create_table(
        "rehearsals",
        sa.Column("rehearsal_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("presentation_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="CREATED", nullable=False),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_rehearsals_presentation_id_presentations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("rehearsal_id", name=op.f("pk_rehearsals")),
        sa.UniqueConstraint(
            "presentation_id",
            "attempt_number",
            name=op.f("uq_rehearsals_presentation_id_attempt_number"),
        ),
    )
    op.create_index(op.f("ix_rehearsals_deleted_at"), "rehearsals", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_rehearsals_presentation_id"), "rehearsals", ["presentation_id"], unique=False)
    op.create_index(op.f("ix_rehearsals_status"), "rehearsals", ["status"], unique=False)

    op.create_table(
        "rehearsal_media",
        sa.Column("media_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_bucket", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_rehearsal_media_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("media_id", name=op.f("pk_rehearsal_media")),
    )
    op.create_index(op.f("ix_rehearsal_media_deleted_at"), "rehearsal_media", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_rehearsal_media_media_type"), "rehearsal_media", ["media_type"], unique=False)
    op.create_index(op.f("ix_rehearsal_media_rehearsal_id"), "rehearsal_media", ["rehearsal_id"], unique=False)
    op.create_index(op.f("ix_rehearsal_media_status"), "rehearsal_media", ["status"], unique=False)

    op.create_table(
        "audio_analyses",
        sa.Column("audio_analysis_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("words_per_minute", sa.Numeric(6, 2), nullable=True),
        sa.Column("filler_word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("silence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("omission_summary", jsonb, nullable=True),
        sa.Column("additional_content_summary", jsonb, nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_audio_analyses_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("audio_analysis_id", name=op.f("pk_audio_analyses")),
        sa.UniqueConstraint("rehearsal_id", name=op.f("uq_audio_analyses_rehearsal_id")),
    )
    op.create_index(op.f("ix_audio_analyses_rehearsal_id"), "audio_analyses", ["rehearsal_id"], unique=True)
    op.create_index(op.f("ix_audio_analyses_status"), "audio_analyses", ["status"], unique=False)

    op.create_table(
        "filler_word_events",
        sa.Column("filler_word_event_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("audio_analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("filler_word", sa.String(length=50), nullable=False),
        sa.Column("start_seconds", sa.Numeric(10, 3), nullable=False),
        sa.Column("end_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("transcript_excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["audio_analysis_id"],
            ["audio_analyses.audio_analysis_id"],
            name=op.f("fk_filler_word_events_audio_analysis_id_audio_analyses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("filler_word_event_id", name=op.f("pk_filler_word_events")),
    )
    op.create_index(
        op.f("ix_filler_word_events_audio_analysis_id"),
        "filler_word_events",
        ["audio_analysis_id"],
        unique=False,
    )
    op.create_index(op.f("ix_filler_word_events_filler_word"), "filler_word_events", ["filler_word"], unique=False)

    op.create_table(
        "speech_events",
        sa.Column("speech_event_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("audio_analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("start_seconds", sa.Numeric(10, 3), nullable=False),
        sa.Column("end_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("transcript_excerpt", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("details", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["audio_analysis_id"],
            ["audio_analyses.audio_analysis_id"],
            name=op.f("fk_speech_events_audio_analysis_id_audio_analyses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("speech_event_id", name=op.f("pk_speech_events")),
    )
    op.create_index(op.f("ix_speech_events_audio_analysis_id"), "speech_events", ["audio_analysis_id"], unique=False)
    op.create_index(op.f("ix_speech_events_event_type"), "speech_events", ["event_type"], unique=False)

    op.create_table(
        "pose_analyses",
        sa.Column("pose_analysis_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("posture_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("stability_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("movement_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_metrics", jsonb, nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_pose_analyses_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pose_analysis_id", name=op.f("pk_pose_analyses")),
        sa.UniqueConstraint("rehearsal_id", name=op.f("uq_pose_analyses_rehearsal_id")),
    )
    op.create_index(op.f("ix_pose_analyses_rehearsal_id"), "pose_analyses", ["rehearsal_id"], unique=True)
    op.create_index(op.f("ix_pose_analyses_status"), "pose_analyses", ["status"], unique=False)

    op.create_table(
        "pose_events",
        sa.Column("pose_event_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("pose_analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("start_seconds", sa.Numeric(10, 3), nullable=False),
        sa.Column("end_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("details", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pose_analysis_id"],
            ["pose_analyses.pose_analysis_id"],
            name=op.f("fk_pose_events_pose_analysis_id_pose_analyses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pose_event_id", name=op.f("pk_pose_events")),
    )
    op.create_index(op.f("ix_pose_events_event_type"), "pose_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_pose_events_pose_analysis_id"), "pose_events", ["pose_analysis_id"], unique=False)

    op.create_table(
        "gaze_analyses",
        sa.Column("gaze_analysis_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("professor_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("screen_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("floor_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("offscreen_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("dominant_target", sa.String(length=50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_metrics", jsonb, nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_gaze_analyses_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("gaze_analysis_id", name=op.f("pk_gaze_analyses")),
        sa.UniqueConstraint("rehearsal_id", name=op.f("uq_gaze_analyses_rehearsal_id")),
    )
    op.create_index(op.f("ix_gaze_analyses_rehearsal_id"), "gaze_analyses", ["rehearsal_id"], unique=True)
    op.create_index(op.f("ix_gaze_analyses_status"), "gaze_analyses", ["status"], unique=False)

    op.create_table(
        "gaze_events",
        sa.Column("gaze_event_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("gaze_analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("target", sa.String(length=50), nullable=False),
        sa.Column("start_seconds", sa.Numeric(10, 3), nullable=False),
        sa.Column("end_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("details", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gaze_analysis_id"],
            ["gaze_analyses.gaze_analysis_id"],
            name=op.f("fk_gaze_events_gaze_analysis_id_gaze_analyses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("gaze_event_id", name=op.f("pk_gaze_events")),
    )
    op.create_index(op.f("ix_gaze_events_event_type"), "gaze_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_gaze_events_gaze_analysis_id"), "gaze_events", ["gaze_analysis_id"], unique=False)
    op.create_index(op.f("ix_gaze_events_target"), "gaze_events", ["target"], unique=False)

    op.create_table(
        "rehearsal_slide_results",
        sa.Column("rehearsal_slide_result_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=False),
        sa.Column("slide_id", sa.BigInteger(), nullable=False),
        sa.Column("planned_seconds", sa.Integer(), nullable=False),
        sa.Column("actual_seconds", sa.Integer(), nullable=False),
        sa.Column("delta_seconds", sa.Integer(), nullable=False),
        sa.Column("started_at_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("ended_at_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("coverage_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("omitted_keywords", jsonb, nullable=True),
        sa.Column("extra_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_rehearsal_slide_results_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slide_id"],
            ["slides.slide_id"],
            name=op.f("fk_rehearsal_slide_results_slide_id_slides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("rehearsal_slide_result_id", name=op.f("pk_rehearsal_slide_results")),
        sa.UniqueConstraint(
            "rehearsal_id",
            "slide_id",
            name=op.f("uq_rehearsal_slide_results_rehearsal_id_slide_id"),
        ),
    )
    op.create_index(
        op.f("ix_rehearsal_slide_results_rehearsal_id"),
        "rehearsal_slide_results",
        ["rehearsal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rehearsal_slide_results_slide_id"),
        "rehearsal_slide_results",
        ["slide_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop rehearsal analysis tables."""

    op.drop_index(op.f("ix_rehearsal_slide_results_slide_id"), table_name="rehearsal_slide_results")
    op.drop_index(op.f("ix_rehearsal_slide_results_rehearsal_id"), table_name="rehearsal_slide_results")
    op.drop_table("rehearsal_slide_results")
    op.drop_index(op.f("ix_gaze_events_target"), table_name="gaze_events")
    op.drop_index(op.f("ix_gaze_events_gaze_analysis_id"), table_name="gaze_events")
    op.drop_index(op.f("ix_gaze_events_event_type"), table_name="gaze_events")
    op.drop_table("gaze_events")
    op.drop_index(op.f("ix_gaze_analyses_status"), table_name="gaze_analyses")
    op.drop_index(op.f("ix_gaze_analyses_rehearsal_id"), table_name="gaze_analyses")
    op.drop_table("gaze_analyses")
    op.drop_index(op.f("ix_pose_events_pose_analysis_id"), table_name="pose_events")
    op.drop_index(op.f("ix_pose_events_event_type"), table_name="pose_events")
    op.drop_table("pose_events")
    op.drop_index(op.f("ix_pose_analyses_status"), table_name="pose_analyses")
    op.drop_index(op.f("ix_pose_analyses_rehearsal_id"), table_name="pose_analyses")
    op.drop_table("pose_analyses")
    op.drop_index(op.f("ix_speech_events_event_type"), table_name="speech_events")
    op.drop_index(op.f("ix_speech_events_audio_analysis_id"), table_name="speech_events")
    op.drop_table("speech_events")
    op.drop_index(op.f("ix_filler_word_events_filler_word"), table_name="filler_word_events")
    op.drop_index(op.f("ix_filler_word_events_audio_analysis_id"), table_name="filler_word_events")
    op.drop_table("filler_word_events")
    op.drop_index(op.f("ix_audio_analyses_status"), table_name="audio_analyses")
    op.drop_index(op.f("ix_audio_analyses_rehearsal_id"), table_name="audio_analyses")
    op.drop_table("audio_analyses")
    op.drop_index(op.f("ix_rehearsal_media_status"), table_name="rehearsal_media")
    op.drop_index(op.f("ix_rehearsal_media_rehearsal_id"), table_name="rehearsal_media")
    op.drop_index(op.f("ix_rehearsal_media_media_type"), table_name="rehearsal_media")
    op.drop_index(op.f("ix_rehearsal_media_deleted_at"), table_name="rehearsal_media")
    op.drop_table("rehearsal_media")
    op.drop_index(op.f("ix_rehearsals_status"), table_name="rehearsals")
    op.drop_index(op.f("ix_rehearsals_presentation_id"), table_name="rehearsals")
    op.drop_index(op.f("ix_rehearsals_deleted_at"), table_name="rehearsals")
    op.drop_table("rehearsals")
