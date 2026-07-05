"""Add model constraints and lookup indexes.

Revision ID: 20260703_0008
Revises: 20260703_0007
Create Date: 2026-07-03 00:00:07.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260703_0008"
down_revision: str | None = "20260703_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing uniqueness guards and high-frequency lookup indexes."""

    op.create_index(
        op.f("ix_presentations_user_id_status"),
        "presentations",
        ["user_id", "status"],
        unique=False,
    )
    with op.batch_alter_table("presentation_files") as batch_op:
        batch_op.create_unique_constraint(
            op.f("uq_presentation_files_storage_bucket_object_key"),
            ["storage_bucket", "object_key"],
        )
    op.create_index(
        op.f("ix_presentation_files_presentation_id_status"),
        "presentation_files",
        ["presentation_id", "status"],
        unique=False,
    )
    with op.batch_alter_table("slides") as batch_op:
        batch_op.create_unique_constraint(
            op.f("uq_slides_presentation_id_slide_number"),
            ["presentation_id", "slide_number"],
        )
    op.create_index(
        op.f("ix_slides_presentation_id_excluded_sort_order"),
        "slides",
        ["presentation_id", "excluded", "sort_order"],
        unique=False,
    )
    op.create_index(
        op.f("ix_presentation_analyses_presentation_id_status"),
        "presentation_analyses",
        ["presentation_id", "status"],
        unique=False,
    )
    with op.batch_alter_table("slide_analyses") as batch_op:
        batch_op.create_unique_constraint(
            op.f("uq_slide_analyses_presentation_analysis_id_slide_id"),
            ["presentation_analysis_id", "slide_id"],
        )
    op.create_index(
        op.f("ix_slide_timings_slide_id_is_active"),
        "slide_timings",
        ["slide_id", "is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slide_scripts_slide_id_is_active"),
        "slide_scripts",
        ["slide_id", "is_active"],
        unique=False,
    )

    op.create_index(
        op.f("ix_rehearsals_presentation_id_status"),
        "rehearsals",
        ["presentation_id", "status"],
        unique=False,
    )
    with op.batch_alter_table("rehearsal_media") as batch_op:
        batch_op.create_unique_constraint(
            op.f("uq_rehearsal_media_storage_bucket_object_key"),
            ["storage_bucket", "object_key"],
        )
    op.create_index(
        op.f("ix_rehearsal_media_rehearsal_id_media_type_status"),
        "rehearsal_media",
        ["rehearsal_id", "media_type", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_filler_word_events_audio_analysis_id_start_seconds"),
        "filler_word_events",
        ["audio_analysis_id", "start_seconds"],
        unique=False,
    )
    op.create_index(
        op.f("ix_speech_events_audio_analysis_id_event_type"),
        "speech_events",
        ["audio_analysis_id", "event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pose_events_pose_analysis_id_event_type"),
        "pose_events",
        ["pose_analysis_id", "event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gaze_events_gaze_analysis_id_event_type"),
        "gaze_events",
        ["gaze_analysis_id", "event_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_agent_evaluations_rehearsal_id_agent_type_status"),
        "agent_evaluations",
        ["rehearsal_id", "agent_type", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_final_reports_rehearsal_id_is_latest"),
        "final_reports",
        ["rehearsal_id", "is_latest"],
        unique=False,
    )

    op.create_index(op.f("ix_jobs_user_id_status"), "jobs", ["user_id", "status"], unique=False)
    op.create_index(
        op.f("ix_jobs_presentation_id_job_type_status"),
        "jobs",
        ["presentation_id", "job_type", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_jobs_rehearsal_id_job_type_status"),
        "jobs",
        ["rehearsal_id", "job_type", "status"],
        unique=False,
    )
    with op.batch_alter_table("job_steps") as batch_op:
        batch_op.create_unique_constraint(
            op.f("uq_job_steps_job_id_step_order"),
            ["job_id", "step_order"],
        )


def downgrade() -> None:
    """Remove constraints and indexes added in this revision."""

    with op.batch_alter_table("job_steps") as batch_op:
        batch_op.drop_constraint(op.f("uq_job_steps_job_id_step_order"), type_="unique")
    op.drop_index(op.f("ix_jobs_rehearsal_id_job_type_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_presentation_id_job_type_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_user_id_status"), table_name="jobs")

    op.drop_index(op.f("ix_final_reports_rehearsal_id_is_latest"), table_name="final_reports")
    op.drop_index(op.f("ix_agent_evaluations_rehearsal_id_agent_type_status"), table_name="agent_evaluations")

    op.drop_index(op.f("ix_gaze_events_gaze_analysis_id_event_type"), table_name="gaze_events")
    op.drop_index(op.f("ix_pose_events_pose_analysis_id_event_type"), table_name="pose_events")
    op.drop_index(op.f("ix_speech_events_audio_analysis_id_event_type"), table_name="speech_events")
    op.drop_index(op.f("ix_filler_word_events_audio_analysis_id_start_seconds"), table_name="filler_word_events")
    op.drop_index(op.f("ix_rehearsal_media_rehearsal_id_media_type_status"), table_name="rehearsal_media")
    with op.batch_alter_table("rehearsal_media") as batch_op:
        batch_op.drop_constraint(op.f("uq_rehearsal_media_storage_bucket_object_key"), type_="unique")
    op.drop_index(op.f("ix_rehearsals_presentation_id_status"), table_name="rehearsals")

    op.drop_index(op.f("ix_slide_scripts_slide_id_is_active"), table_name="slide_scripts")
    op.drop_index(op.f("ix_slide_timings_slide_id_is_active"), table_name="slide_timings")
    with op.batch_alter_table("slide_analyses") as batch_op:
        batch_op.drop_constraint(op.f("uq_slide_analyses_presentation_analysis_id_slide_id"), type_="unique")
    op.drop_index(op.f("ix_presentation_analyses_presentation_id_status"), table_name="presentation_analyses")
    op.drop_index(op.f("ix_slides_presentation_id_excluded_sort_order"), table_name="slides")
    with op.batch_alter_table("slides") as batch_op:
        batch_op.drop_constraint(op.f("uq_slides_presentation_id_slide_number"), type_="unique")
    op.drop_index(op.f("ix_presentation_files_presentation_id_status"), table_name="presentation_files")
    with op.batch_alter_table("presentation_files") as batch_op:
        batch_op.drop_constraint(op.f("uq_presentation_files_storage_bucket_object_key"), type_="unique")
    op.drop_index(op.f("ix_presentations_user_id_status"), table_name="presentations")
