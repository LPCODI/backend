"""Shared FastAPI dependencies for authenticated API endpoints."""

from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import AccessTokenError, ApiError, Settings, decode_access_token, get_settings
from app.db import get_db
from app.domain import ErrorCode, UserStatus
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

AUTHENTICATION_REQUIRED_MESSAGE = "인증이 필요합니다."
TOKEN_INVALID_MESSAGE = "유효하지 않은 인증 토큰입니다."
TOKEN_EXPIRED_MESSAGE = "인증 토큰이 만료되었습니다."
USER_NOT_FOUND_MESSAGE = "로그인 사용자를 찾을 수 없습니다."
USER_INACTIVE_MESSAGE = "비활성화된 사용자입니다."


def _auth_error(code: ErrorCode, message: str) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.UNAUTHORIZED,
        code=code,
        message=message,
    )


def _permission_error(message: str) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.FORBIDDEN,
        code=ErrorCode.PERMISSION_DENIED,
        message=message,
    )


def get_request_settings(request: Request) -> Settings:
    """Return settings attached to the running FastAPI app."""

    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> User:
    """Resolve and validate the user attached to a Bearer access token."""

    if not token:
        raise _auth_error(ErrorCode.AUTHENTICATION_REQUIRED, AUTHENTICATION_REQUIRED_MESSAGE)

    try:
        payload = decode_access_token(token, settings=settings)
    except AccessTokenError as exc:
        message = TOKEN_EXPIRED_MESSAGE if exc.code == ErrorCode.TOKEN_EXPIRED else TOKEN_INVALID_MESSAGE
        raise _auth_error(exc.code, message) from exc

    statement = select(User).where(
        User.user_id == payload.user_id,
        User.deleted_at.is_(None),
    )
    user = db.execute(statement).scalar_one_or_none()
    if user is None:
        raise _auth_error(ErrorCode.USER_NOT_FOUND, USER_NOT_FOUND_MESSAGE)
    if user.status != UserStatus.ACTIVE:
        raise _permission_error(USER_INACTIVE_MESSAGE)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


__all__ = [
    "AUTHENTICATION_REQUIRED_MESSAGE",
    "CurrentUser",
    "TOKEN_EXPIRED_MESSAGE",
    "TOKEN_INVALID_MESSAGE",
    "USER_INACTIVE_MESSAGE",
    "USER_NOT_FOUND_MESSAGE",
    "get_current_user",
    "get_request_settings",
    "oauth2_scheme",
]
