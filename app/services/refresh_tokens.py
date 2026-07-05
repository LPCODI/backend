"""Refresh token persistence, validation, rotation, and revocation service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.refresh_tokens import generate_refresh_token, hash_refresh_token
from app.core.tokens import create_access_token
from app.domain import ErrorCode
from app.models import RefreshToken


@dataclass(frozen=True)
class RefreshTokenIssue:
    """A newly issued refresh token and its persistence record."""

    raw_token: str
    record: RefreshToken


@dataclass(frozen=True)
class TokenPair:
    """Access and refresh token pair returned by login or refresh flows."""

    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


@dataclass(frozen=True)
class RefreshTokenRotation:
    """Result of revoking one refresh token and issuing its replacement."""

    old_record: RefreshToken
    issue: RefreshTokenIssue


class RefreshTokenError(ValueError):
    """Raised when a refresh token cannot be used."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _next_sqlite_refresh_token_id(session: Session) -> int | None:
    """Return a refresh token id for SQLite BIGINT identity test databases."""

    bind = session.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = session.execute(
        select(func.coalesce(func.max(RefreshToken.refresh_token_id), 0) + 1)
    ).scalar_one()
    return int(next_id)


class RefreshTokenService:
    """Manage refresh token storage, reissue, and logout revocation."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def issue_refresh_token(
        self,
        *,
        user_id: int,
        issued_at: datetime | None = None,
    ) -> RefreshTokenIssue:
        """Create a raw refresh token and store only its hash."""

        if user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        now = _as_aware_utc(issued_at or _utc_now())
        raw_token = generate_refresh_token()
        token_kwargs: dict[str, object] = {
            "user_id": user_id,
            "token_hash": hash_refresh_token(raw_token),
            "expires_at": now + timedelta(days=self.settings.refresh_token_expire_days),
        }
        sqlite_token_id = _next_sqlite_refresh_token_id(self.session)
        if sqlite_token_id is not None:
            token_kwargs["refresh_token_id"] = sqlite_token_id

        record = RefreshToken(**token_kwargs)
        self.session.add(record)
        return RefreshTokenIssue(raw_token=raw_token, record=record)

    def get_active_refresh_token(
        self,
        raw_token: str,
        *,
        now: datetime | None = None,
    ) -> RefreshToken:
        """Return the active stored token for a raw refresh token value."""

        token_hash = hash_refresh_token(raw_token)
        statement: Select[tuple[RefreshToken]] = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        record = self.session.execute(statement).scalar_one_or_none()
        if record is None:
            raise RefreshTokenError(ErrorCode.TOKEN_INVALID, "Refresh token is invalid.")
        if record.is_revoked:
            raise RefreshTokenError(ErrorCode.TOKEN_INVALID, "Refresh token has been revoked.")

        checked_at = _as_aware_utc(now or _utc_now())
        if _as_aware_utc(record.expires_at) <= checked_at:
            raise RefreshTokenError(ErrorCode.TOKEN_EXPIRED, "Refresh token has expired.")

        return record

    def revoke_refresh_token(
        self,
        raw_token: str,
        *,
        revoked_at: datetime | None = None,
    ) -> RefreshToken:
        """Revoke one active refresh token, as used by logout."""

        checked_at = _as_aware_utc(revoked_at or _utc_now())
        record = self.get_active_refresh_token(raw_token, now=checked_at)
        record.revoke(checked_at)
        return record

    def revoke_user_refresh_tokens(
        self,
        *,
        user_id: int,
        revoked_at: datetime | None = None,
    ) -> int:
        """Revoke every non-revoked refresh token for a user."""

        if user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        checked_at = _as_aware_utc(revoked_at or _utc_now())
        records = self.session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        ).all()
        for record in records:
            record.revoke(checked_at)
        return len(records)

    def rotate_refresh_token(
        self,
        raw_token: str,
        *,
        rotated_at: datetime | None = None,
    ) -> RefreshTokenRotation:
        """Revoke a refresh token and issue a replacement for the same user."""

        checked_at = _as_aware_utc(rotated_at or _utc_now())
        old_record = self.get_active_refresh_token(raw_token, now=checked_at)
        old_record.revoke(checked_at)
        issue = self.issue_refresh_token(user_id=old_record.user_id, issued_at=checked_at)
        return RefreshTokenRotation(old_record=old_record, issue=issue)

    def refresh_token_pair(
        self,
        raw_token: str,
        *,
        issued_at: datetime | None = None,
    ) -> TokenPair:
        """Rotate the refresh token and issue a new access token."""

        now = _as_aware_utc(issued_at or _utc_now())
        rotation = self.rotate_refresh_token(raw_token, rotated_at=now)
        access_token = create_access_token(
            user_id=rotation.old_record.user_id,
            settings=self.settings,
            issued_at=now,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=rotation.issue.raw_token,
            access_token_expires_at=now + timedelta(minutes=self.settings.access_token_expire_minutes),
            refresh_token_expires_at=rotation.issue.record.expires_at,
        )


__all__ = [
    "RefreshTokenError",
    "RefreshTokenIssue",
    "RefreshTokenRotation",
    "RefreshTokenService",
    "TokenPair",
]
