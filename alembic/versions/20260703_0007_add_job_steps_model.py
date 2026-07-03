"""Add asynchronous job steps table.

Revision ID: 20260703_0007
Revises: 20260703_0006
Create Date: 2026-07-03 00:00:06.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0007"
down_revision: str | None = "20260703_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create job_steps table for ordered task stage progress."""

    is_postgresql = op.get_context().dialect.name == "postgresql"
    job_id_type = postgresql.UUID(as_uuid=True) if is_postgresql else sa.String(length=36)
    op.create_table(
        "job_steps",
        sa.Column("job_step_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job_id", job_id_type, nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            name=op.f("fk_job_steps_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_step_id", name=op.f("pk_job_steps")),
    )
    op.create_index(op.f("ix_job_steps_job_id"), "job_steps", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_steps_status"), "job_steps", ["status"], unique=False)
    op.create_index(op.f("ix_job_steps_step_order"), "job_steps", ["step_order"], unique=False)


def downgrade() -> None:
    """Drop job_steps table."""

    op.drop_index(op.f("ix_job_steps_step_order"), table_name="job_steps")
    op.drop_index(op.f("ix_job_steps_status"), table_name="job_steps")
    op.drop_index(op.f("ix_job_steps_job_id"), table_name="job_steps")
    op.drop_table("job_steps")
