"""Authentication API routes."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_request_settings
from app.core import Settings
from app.db import get_db
from app.schemas import SuccessResponse
from app.schemas.auth import (
    AuthTag,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    SignupRequest,
    TokenPairResponse,
    UserResponse,
)
from app.services import (
    create_user_account,
    login_user_account,
    logout_user_account,
    refresh_user_token_pair,
)

router = APIRouter(prefix="/auth", tags=[AuthTag.AUTH])


@router.post(
    "/signup",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
def signup(
    request: SignupRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[UserResponse]:
    """Create a user account."""

    user = create_user_account(
        db,
        email=request.email,
        password=request.password,
        name=request.name,
    )
    return SuccessResponse(
        data=UserResponse.model_validate(user),
        message=HTTPStatus.CREATED.phrase,
    )


@router.post(
    "/login",
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_200_OK,
)
def login(
    request: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> SuccessResponse[TokenPairResponse]:
    """Issue access and refresh tokens for valid credentials."""

    result = login_user_account(
        db,
        email=request.email,
        password=request.password,
        settings=settings,
    )
    return SuccessResponse(
        data=TokenPairResponse(
            access_token=result.token_pair.access_token,
            refresh_token=result.token_pair.refresh_token,
            access_token_expires_at=result.token_pair.access_token_expires_at,
            refresh_token_expires_at=result.token_pair.refresh_token_expires_at,
            user=UserResponse.model_validate(result.user),
        )
    )


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenPairResponse],
    status_code=status.HTTP_200_OK,
)
def refresh(
    request: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> SuccessResponse[TokenPairResponse]:
    """Rotate a refresh token and issue a new access token."""

    result = refresh_user_token_pair(
        db,
        refresh_token=request.refresh_token,
        settings=settings,
    )
    return SuccessResponse(
        data=TokenPairResponse(
            access_token=result.token_pair.access_token,
            refresh_token=result.token_pair.refresh_token,
            access_token_expires_at=result.token_pair.access_token_expires_at,
            refresh_token_expires_at=result.token_pair.refresh_token_expires_at,
            user=UserResponse.model_validate(result.user),
        )
    )


@router.post(
    "/logout",
    response_model=SuccessResponse[LogoutResponse],
    status_code=status.HTTP_200_OK,
)
def logout(
    request: LogoutRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> SuccessResponse[LogoutResponse]:
    """Revoke the current user's refresh token."""

    logout_user_account(
        db,
        user=current_user,
        refresh_token=request.refresh_token,
        settings=settings,
    )
    return SuccessResponse(data=LogoutResponse(revoked=True))
