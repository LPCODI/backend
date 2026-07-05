"""Authentication request and response schemas."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from app.domain import UserRole, UserStatus

EmailString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
PasswordString = Annotated[str, StringConstraints(min_length=8, max_length=128)]
NameString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ProfileImageUrlString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2048),
]


class SignupRequest(BaseModel):
    """Request body for creating a user account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailString
    password: PasswordString
    name: NameString

    @field_validator("password")
    @classmethod
    def password_must_not_be_blank(cls, value: str) -> str:
        """Reject passwords that satisfy length only through whitespace."""

        if not value.strip():
            raise ValueError("Password must not be blank.")
        return value


class LoginRequest(BaseModel):
    """Request body for issuing access and refresh tokens."""

    model_config = ConfigDict(extra="forbid")

    email: EmailString
    password: PasswordString

    @field_validator("password")
    @classmethod
    def password_must_not_be_blank(cls, value: str) -> str:
        """Reject passwords that satisfy length only through whitespace."""

        if not value.strip():
            raise ValueError("Password must not be blank.")
        return value


class RefreshTokenRequest(BaseModel):
    """Request body for rotating a refresh token and issuing a new token pair."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


class LogoutRequest(BaseModel):
    """Request body for revoking one refresh token during logout."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


class LogoutResponse(BaseModel):
    """Response body returned after logout revokes a refresh token."""

    model_config = ConfigDict(extra="forbid")

    revoked: bool


class UserUpdateRequest(BaseModel):
    """Request body for updating the authenticated user's editable profile fields."""

    model_config = ConfigDict(extra="forbid")

    name: NameString | None = None
    profile_image_url: ProfileImageUrlString | None = None

    @model_validator(mode="after")
    def at_least_one_field_must_be_provided(self) -> "UserUpdateRequest":
        """Reject empty profile update requests."""

        if not self.model_fields_set:
            raise ValueError("At least one editable user field must be provided.")
        return self


class UserResponse(BaseModel):
    """Public user profile returned by authentication and user APIs."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    user_id: int
    email: str
    name: str
    profile_image_url: str | None = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class TokenPairResponse(BaseModel):
    """Token pair returned by login and token refresh APIs."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    user: UserResponse


class AuthTag(StrEnum):
    """OpenAPI tags used by authentication routers."""

    AUTH = "인증"


__all__ = [
    "AuthTag",
    "EmailString",
    "LoginRequest",
    "LogoutRequest",
    "LogoutResponse",
    "NameString",
    "PasswordString",
    "ProfileImageUrlString",
    "RefreshTokenRequest",
    "SignupRequest",
    "TokenPairResponse",
    "UserUpdateRequest",
    "UserResponse",
]
