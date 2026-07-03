"""Initial migration baseline.

Revision ID: 20260703_0001
Revises:
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence


revision: str = "20260703_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish the first Alembic revision before domain tables are added."""

    pass


def downgrade() -> None:
    """Return to the pre-migration baseline."""

    pass
