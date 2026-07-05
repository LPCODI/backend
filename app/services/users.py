"""User account service functions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import (
    ApiError,
    Settings,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain import ErrorCode, UserStatus
from app.models import User
from app.services.refresh_tokens import RefreshTokenError, RefreshTokenService, TokenPair

USER_ALREADY_EXISTS_MESSAGE = "이미 가입된 이메일입니다."
INVALID_CREDENTIALS_MESSAGE = "이메일 또는 비밀번호가 올바르지 않습니다."
REFRESH_TOKEN_INVALID_MESSAGE = "Refresh token is invalid."


@dataclass(frozen=True)
class LoginResult:
    """Authenticated user and issued token pair."""

    user: User
    token_pair: TokenPair


@dataclass(frozen=True)
class TokenRefreshResult:
    """User and rotated token pair returned by the refresh API."""

    user: User
    token_pair: TokenPair


def _user_already_exists_error() -> ApiError:
    return ApiError(
        status_code=HTTPStatus.CONFLICT,
        code=ErrorCode.USER_ALREADY_EXISTS,
        message=USER_ALREADY_EXISTS_MESSAGE,
    )


def _invalid_credentials_error() -> ApiError:
    return ApiError(
        status_code=HTTPStatus.UNAUTHORIZED,
        code=ErrorCode.INVALID_CREDENTIALS,
        message=INVALID_CREDENTIALS_MESSAGE,
    )


def _invalid_refresh_token_error(
    *,
    code: ErrorCode = ErrorCode.TOKEN_INVALID,
    message: str = REFRESH_TOKEN_INVALID_MESSAGE,
) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.UNAUTHORIZED,
        code=code,
        message=message,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _next_sqlite_user_id(db: Session) -> int | None:
    """Return a user id for SQLite, whose BIGINT identity columns do not autoincrement."""

    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(User.user_id), 0) + 1)).scalar_one()
    return int(next_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a non-deleted user by normalized email."""

    normalized_email = email.strip().lower()
    statement = select(User).where(
        func.lower(User.email) == normalized_email,
        User.deleted_at.is_(None),
    )
    return db.execute(statement).scalar_one_or_none()


def create_user_account(
    db: Session,
    *,
    email: str,
    password: str,
    name: str,
) -> User:
    """Create and persist a user account."""

    normalized_email = email.strip().lower()
    if get_user_by_email(db, normalized_email) is not None:
        raise _user_already_exists_error()

    user_kwargs: dict[str, object] = {
        "email": normalized_email,
        "password_hash": hash_password(password),
        "name": name.strip(),
    }
    sqlite_user_id = _next_sqlite_user_id(db)
    if sqlite_user_id is not None:
        user_kwargs["user_id"] = sqlite_user_id

    user = User(**user_kwargs)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _user_already_exists_error() from exc

    db.refresh(user)
    return user


def login_user_account(
    db: Session,
    *,
    email: str,
    password: str,
    settings: Settings,
) -> LoginResult:
    """Validate credentials, persist login state, and issue token pair."""

    user = get_user_by_email(db, email)
    if user is None or user.status != UserStatus.ACTIVE:
        raise _invalid_credentials_error()
    if not verify_password(password, user.password_hash):
        raise _invalid_credentials_error()

    now = _utc_now()
    user.last_login_at = now
    refresh_issue = RefreshTokenService(db, settings).issue_refresh_token(
        user_id=user.user_id,
        issued_at=now,
    )
    access_token = create_access_token(
        user_id=user.user_id,
        settings=settings,
        issued_at=now,
    )
    token_pair = TokenPair(
        access_token=access_token,
        refresh_token=refresh_issue.raw_token,
        access_token_expires_at=now + timedelta(minutes=settings.access_token_expire_minutes),
        refresh_token_expires_at=refresh_issue.record.expires_at,
    )

    db.commit()
    db.refresh(user)
    return LoginResult(user=user, token_pair=token_pair)


def refresh_user_token_pair(
    db: Session,
    *,
    refresh_token: str,
    settings: Settings,
) -> TokenRefreshResult:
    """Rotate a valid refresh token and return a new access/refresh token pair."""

    service = RefreshTokenService(db, settings)
    try:
        token_pair = service.refresh_token_pair(refresh_token)
    except RefreshTokenError as exc:
        db.rollback()
        raise _invalid_refresh_token_error(code=exc.code, message=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise _invalid_refresh_token_error() from exc

    access_payload = decode_access_token(token_pair.access_token, settings=settings)
    user = db.get(User, access_payload.user_id)
    if user is None or user.deleted_at is not None or user.status != UserStatus.ACTIVE:
        db.rollback()
        raise _invalid_refresh_token_error()

    db.commit()
    db.refresh(user)
    return TokenRefreshResult(user=user, token_pair=token_pair)


def logout_user_account(
    db: Session,
    *,
    user: User,
    refresh_token: str,
    settings: Settings,
) -> None:
    """Revoke a user's active refresh token during logout."""

    service = RefreshTokenService(db, settings)
    try:
        record = service.get_active_refresh_token(refresh_token)
    except RefreshTokenError as exc:
        db.rollback()
        raise _invalid_refresh_token_error(code=exc.code, message=str(exc)) from exc

    if record.user_id != user.user_id:
        db.rollback()
        raise _invalid_refresh_token_error()

    record.revoke(_utc_now())
    db.commit()


def update_user_profile(
    db: Session,
    *,
    user: User,
    name: str | None = None,
    profile_image_url: str | None = None,
    update_profile_image_url: bool = False,
) -> User:
    """Update editable profile fields for an authenticated user."""

    if name is not None:
        user.name = name.strip()
    if update_profile_image_url:
        user.profile_image_url = profile_image_url.strip() if profile_image_url is not None else None

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


__all__ = [
    "INVALID_CREDENTIALS_MESSAGE",
    "LoginResult",
    "REFRESH_TOKEN_INVALID_MESSAGE",
    "TokenRefreshResult",
    "USER_ALREADY_EXISTS_MESSAGE",
    "create_user_account",
    "get_user_by_email",
    "login_user_account",
    "logout_user_account",
    "refresh_user_token_pair",
    "update_user_profile",
]
