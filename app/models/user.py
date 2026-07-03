"""User account persistence model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Identity, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin
from app.domain.accounts import DEFAULT_USER_ROLE, DEFAULT_USER_STATUS, UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.presentation import Presentation
    from app.models.refresh_token import RefreshToken


class User(TimestampMixin, SoftDeleteMixin, Base):
    """Application user account and profile."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        String(30),
        default=DEFAULT_USER_ROLE,
        server_default=DEFAULT_USER_ROLE.value,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        String(30),
        default=DEFAULT_USER_STATUS,
        server_default=DEFAULT_USER_STATUS.value,
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    presentations: Mapped[list["Presentation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
