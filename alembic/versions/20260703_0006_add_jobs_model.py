"""Add asynchronous jobs table.

Revision ID: 20260703_0006
Revises: 20260703_0005
Create Date: 2026-07-03 00:00:05.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0006"
down_revision: str | None = "20260703_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create jobs table for queued and running long-running tasks."""

    is_postgresql = op.get_context().dialect.name == "postgresql"
    if is_postgresql:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    job_id_type = postgresql.UUID(as_uuid=True) if is_postgresql else sa.String(length=36)
    job_id_default = sa.text("gen_random_uuid()") if is_postgresql else None
    op.create_table(
        "jobs",
        sa.Column("job_id", job_id_type, server_default=job_id_default, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("presentation_id", sa.BigInteger(), nullable=True),
        sa.Column("rehearsal_id", sa.BigInteger(), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("request_payload", jsonb, nullable=True),
        sa.Column("result_payload", jsonb, nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_task_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.presentation_id"],
            name=op.f("fk_jobs_presentation_id_presentations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rehearsal_id"],
            ["rehearsals.rehearsal_id"],
            name=op.f("fk_jobs_rehearsal_id_rehearsals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name=op.f("fk_jobs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_job_type"), "jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_jobs_presentation_id"), "jobs", ["presentation_id"], unique=False)
    op.create_index(op.f("ix_jobs_rehearsal_id"), "jobs", ["rehearsal_id"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_jobs_worker_task_id"), "jobs", ["worker_task_id"], unique=False)


def downgrade() -> None:
    """Drop jobs table."""

    op.drop_index(op.f("ix_jobs_worker_task_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_rehearsal_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_presentation_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_job_type"), table_name="jobs")
    op.drop_table("jobs")
