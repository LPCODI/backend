"""Shared SQLAlchemy declarative base and model mixins."""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Identity, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class BigIntPrimaryKeyMixin:
    """BIGINT identity primary key strategy for regular domain tables."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )


class TimestampMixin:
    """Timezone-aware creation and update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete marker shared by user-owned data tables."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return whether this row has been soft-deleted."""

        return self.deleted_at is not None

    def soft_delete(self, deleted_at: datetime | None = None) -> None:
        """Mark the row as deleted without physically removing it."""

        self.deleted_at = deleted_at or datetime.now(UTC)


class BaseModel(BigIntPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Abstract base for standard persistent domain models."""

    __abstract__ = True
