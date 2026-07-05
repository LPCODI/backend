"""JWT access token helpers for API authentication."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import Settings
from app.domain import ErrorCode

ACCESS_TOKEN_TYPE = "access"
TOKEN_TYPE_CLAIM = "token_type"


@dataclass(frozen=True)
class AccessTokenPayload:
    """Validated access token claims used by authenticated requests."""

    user_id: int
    issued_at: datetime
    expires_at: datetime


class AccessTokenError(ValueError):
    """Raised when an access token cannot be trusted."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _secret_value(settings: Settings) -> str:
    return settings.jwt_secret_key.get_secret_value()


def _timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _datetime_from_claim(claims: dict[str, Any], name: str) -> datetime:
    value = claims.get(name)
    if not isinstance(value, int):
        raise AccessTokenError(ErrorCode.TOKEN_INVALID, f"Token claim '{name}' is invalid.")
    return datetime.fromtimestamp(value, UTC)


def create_access_token(
    *,
    user_id: int,
    settings: Settings,
    issued_at: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for a user id."""

    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    now = issued_at or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = now + lifetime
    claims = {
        "sub": str(user_id),
        TOKEN_TYPE_CLAIM: ACCESS_TOKEN_TYPE,
        "iat": _timestamp(now),
        "exp": _timestamp(expires_at),
    }
    return jwt.encode(
        claims,
        _secret_value(settings),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, *, settings: Settings) -> AccessTokenPayload:
    """Decode and validate a signed JWT access token."""

    try:
        claims = jwt.decode(
            token,
            _secret_value(settings),
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise AccessTokenError(ErrorCode.TOKEN_EXPIRED, "Access token has expired.") from exc
    except JWTError as exc:
        raise AccessTokenError(ErrorCode.TOKEN_INVALID, "Access token is invalid.") from exc

    if claims.get(TOKEN_TYPE_CLAIM) != ACCESS_TOKEN_TYPE:
        raise AccessTokenError(ErrorCode.TOKEN_INVALID, "Token type is not access.")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise AccessTokenError(ErrorCode.TOKEN_INVALID, "Token subject is invalid.")

    user_id = int(subject)
    if user_id <= 0:
        raise AccessTokenError(ErrorCode.TOKEN_INVALID, "Token subject is invalid.")

    return AccessTokenPayload(
        user_id=user_id,
        issued_at=_datetime_from_claim(claims, "iat"),
        expires_at=_datetime_from_claim(claims, "exp"),
    )


__all__ = [
    "ACCESS_TOKEN_TYPE",
    "TOKEN_TYPE_CLAIM",
    "AccessTokenError",
    "AccessTokenPayload",
    "create_access_token",
    "decode_access_token",
]
