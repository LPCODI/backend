"""Add slide script revision history metadata.

Revision ID: 20260709_0009
Revises: 20260703_0008
Create Date: 2026-07-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260709_0009"
down_revision: str | None = "20260703_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add previous-version and user-edit metadata to slide scripts."""

    with op.batch_alter_table("slide_scripts") as batch_op:
        batch_op.add_column(sa.Column("previous_slide_script_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("edited_by_user_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("revision_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("user_revision_note", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_slide_scripts_previous_slide_script_id_slide_scripts"),
            "slide_scripts",
            ["previous_slide_script_id"],
            ["slide_script_id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            op.f("fk_slide_scripts_edited_by_user_id_users"),
            "users",
            ["edited_by_user_id"],
            ["user_id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(op.f("ix_slide_scripts_previous_slide_script_id"), ["previous_slide_script_id"])
        batch_op.create_index(op.f("ix_slide_scripts_edited_by_user_id"), ["edited_by_user_id"])


def downgrade() -> None:
    """Remove slide script revision history metadata."""

    with op.batch_alter_table("slide_scripts") as batch_op:
        batch_op.drop_index(op.f("ix_slide_scripts_edited_by_user_id"))
        batch_op.drop_index(op.f("ix_slide_scripts_previous_slide_script_id"))
        batch_op.drop_constraint(op.f("fk_slide_scripts_edited_by_user_id_users"), type_="foreignkey")
        batch_op.drop_constraint(
            op.f("fk_slide_scripts_previous_slide_script_id_slide_scripts"),
            type_="foreignkey",
        )
        batch_op.drop_column("user_revision_note")
        batch_op.drop_column("revision_reason")
        batch_op.drop_column("edited_by_user_id")
        batch_op.drop_column("previous_slide_script_id")
