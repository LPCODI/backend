"""Authenticated user profile API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db import get_db
from app.schemas import SuccessResponse
from app.schemas.auth import UserResponse, UserUpdateRequest
from app.services import update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
def get_me(current_user: CurrentUser) -> SuccessResponse[UserResponse]:
    """Return the authenticated user's public profile."""

    return SuccessResponse(data=UserResponse.model_validate(current_user))


@router.patch(
    "/me",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
def update_me(
    request: UserUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[UserResponse]:
    """Update the authenticated user's editable profile fields."""

    user = update_user_profile(
        db,
        user=current_user,
        name=request.name,
        profile_image_url=request.profile_image_url,
        update_profile_image_url="profile_image_url" in request.model_fields_set,
    )
    return SuccessResponse(data=UserResponse.model_validate(user))
