"""Add presentation content tables.

Revision ID: 20260703_0003
Revises: 20260703_0002
Create Date: 2026-07-03 00:00:02.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0003"
down_revision: str | None = "20260703_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create presentation, file, slide, analysis, timing, and script tables."""

    op.create_table(
        "presentations",
        sa.Column("presentation_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("qa_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("presentation_duration_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "presentation_context",
            sa.String(length=50),
            server_default="UNIVERSITY_PROJECT_FOR_PROFESSOR",
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), server_default="DRAFT", nullable=False),
        sa.Column("timing_status", sa.String(length=30), nullable=True),
        sa.Column("script_status", sa.String(length=30), nullable=True),
        sa.Column("duplicated_from_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["duplicated_from_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_presentations_duplicated_from_id_presentations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name=op.f("fk_presentations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("presentation_id", name=op.f("pk_presentations")),
    )
    op.create_index(op.f("ix_presentations_deleted_at"), "presentations", ["deleted_at"], unique=False)
    op.create_index(
        op.f("ix_presentations_duplicated_from_id"),
        "presentations",
        ["duplicated_from_id"],
        unique=False,
    )
    op.create_index(op.f("ix_presentations_user_id"), "presentations", ["user_id"], unique=False)

    op.create_table(
        "presentation_files",
        sa.Column("file_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("presentation_id", sa.BigInteger(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=True),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_bucket", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("slide_count", sa.Integer(), nullable=True),
        sa.Column("parse_error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_presentation_files_presentation_id_presentations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("file_id", name=op.f("pk_presentation_files")),
    )
    op.create_index(
        op.f("ix_presentation_files_deleted_at"),
        "presentation_files",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_presentation_files_presentation_id"),
        "presentation_files",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_presentation_files_status"), "presentation_files", ["status"], unique=False)

    op.create_table(
        "slides",
        sa.Column("slide_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("presentation_id", sa.BigInteger(), nullable=False),
        sa.Column("file_id", sa.BigInteger(), nullable=False),
        sa.Column("slide_number", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("notes_text", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("image_object_key", sa.Text(), nullable=True),
        sa.Column("excluded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["presentation_files.file_id"],
            name=op.f("fk_slides_file_id_presentation_files"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_slides_presentation_id_presentations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("slide_id", name=op.f("pk_slides")),
        sa.UniqueConstraint(
            "presentation_id",
            "sort_order",
            name=op.f("uq_slides_presentation_id_sort_order"),
        ),
    )
    op.create_index(op.f("ix_slides_file_id"), "slides", ["file_id"], unique=False)
    op.create_index(op.f("ix_slides_presentation_id"), "slides", ["presentation_id"], unique=False)

    op.create_table(
        "presentation_analyses",
        sa.Column("presentation_analysis_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("presentation_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("overall_core_message", sa.Text(), nullable=True),
        sa.Column("strengths", jsonb, nullable=True),
        sa.Column("weaknesses", jsonb, nullable=True),
        sa.Column("professor_question_points", jsonb, nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_presentation_analyses_presentation_id_presentations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("presentation_analysis_id", name=op.f("pk_presentation_analyses")),
        sa.UniqueConstraint(
            "presentation_id",
            "version",
            name=op.f("uq_presentation_analyses_presentation_id_version"),
        ),
    )
    op.create_index(
        op.f("ix_presentation_analyses_presentation_id"),
        "presentation_analyses",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_presentation_analyses_status"),
        "presentation_analyses",
        ["status"],
        unique=False,
    )

    op.create_table(
        "slide_analyses",
        sa.Column("slide_analysis_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("presentation_analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("slide_id", sa.BigInteger(), nullable=False),
        sa.Column("importance_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("complexity_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("core_message", sa.Text(), nullable=True),
        sa.Column("missing_explanations", jsonb, nullable=True),
        sa.Column("expected_questions", jsonb, nullable=True),
        sa.Column("keywords", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["presentation_analysis_id"],
            ["presentation_analyses.presentation_analysis_id"],
            name=op.f("fk_slide_analyses_presentation_analysis_id_presentation_analyses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slide_id"],
            ["slides.slide_id"],
            name=op.f("fk_slide_analyses_slide_id_slides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("slide_analysis_id", name=op.f("pk_slide_analyses")),
    )
    op.create_index(
        op.f("ix_slide_analyses_presentation_analysis_id"),
        "slide_analyses",
        ["presentation_analysis_id"],
        unique=False,
    )
    op.create_index(op.f("ix_slide_analyses_slide_id"), "slide_analyses", ["slide_id"], unique=False)

    op.create_table(
        "slide_timings",
        sa.Column("slide_timing_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("slide_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("allocated_seconds", sa.Integer(), nullable=False),
        sa.Column("transition_seconds", sa.Integer(), nullable=False),
        sa.Column("allocation_reason", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["slide_id"],
            ["slides.slide_id"],
            name=op.f("fk_slide_timings_slide_id_slides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("slide_timing_id", name=op.f("pk_slide_timings")),
        sa.UniqueConstraint("slide_id", "version", name=op.f("uq_slide_timings_slide_id_version")),
    )
    op.create_index(op.f("ix_slide_timings_slide_id"), "slide_timings", ["slide_id"], unique=False)

    op.create_table(
        "slide_scripts",
        sa.Column("slide_script_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("slide_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("script_text", sa.Text(), nullable=False),
        sa.Column("core_message", sa.Text(), nullable=True),
        sa.Column("estimated_seconds", sa.Integer(), nullable=True),
        sa.Column("emphasis_words", jsonb, nullable=True),
        sa.Column("transition_sentence", sa.Text(), nullable=True),
        sa.Column("optional_explanation", sa.Text(), nullable=True),
        sa.Column("expected_questions", jsonb, nullable=True),
        sa.Column("generation_type", sa.String(length=30), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["slide_id"],
            ["slides.slide_id"],
            name=op.f("fk_slide_scripts_slide_id_slides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("slide_script_id", name=op.f("pk_slide_scripts")),
        sa.UniqueConstraint("slide_id", "version", name=op.f("uq_slide_scripts_slide_id_version")),
    )
    op.create_index(op.f("ix_slide_scripts_slide_id"), "slide_scripts", ["slide_id"], unique=False)


def downgrade() -> None:
    """Drop presentation content tables."""

    op.drop_index(op.f("ix_slide_scripts_slide_id"), table_name="slide_scripts")
    op.drop_table("slide_scripts")
    op.drop_index(op.f("ix_slide_timings_slide_id"), table_name="slide_timings")
    op.drop_table("slide_timings")
    op.drop_index(op.f("ix_slide_analyses_slide_id"), table_name="slide_analyses")
    op.drop_index(op.f("ix_slide_analyses_presentation_analysis_id"), table_name="slide_analyses")
    op.drop_table("slide_analyses")
    op.drop_index(op.f("ix_presentation_analyses_status"), table_name="presentation_analyses")
    op.drop_index(op.f("ix_presentation_analyses_presentation_id"), table_name="presentation_analyses")
    op.drop_table("presentation_analyses")
    op.drop_index(op.f("ix_slides_presentation_id"), table_name="slides")
    op.drop_index(op.f("ix_slides_file_id"), table_name="slides")
    op.drop_table("slides")
    op.drop_index(op.f("ix_presentation_files_status"), table_name="presentation_files")
    op.drop_index(op.f("ix_presentation_files_presentation_id"), table_name="presentation_files")
    op.drop_index(op.f("ix_presentation_files_deleted_at"), table_name="presentation_files")
    op.drop_table("presentation_files")
    op.drop_index(op.f("ix_presentations_user_id"), table_name="presentations")
    op.drop_index(op.f("ix_presentations_duplicated_from_id"), table_name="presentations")
    op.drop_index(op.f("ix_presentations_deleted_at"), table_name="presentations")
    op.drop_table("presentations")
