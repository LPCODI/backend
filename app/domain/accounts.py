"""Account domain values used by authentication and user models."""

from enum import StrEnum


class UserRole(StrEnum):
    """Supported user roles."""

    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    """Supported account lifecycle states."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


DEFAULT_USER_ROLE = UserRole.USER
DEFAULT_USER_STATUS = UserStatus.ACTIVE


__all__ = [
    "DEFAULT_USER_ROLE",
    "DEFAULT_USER_STATUS",
    "UserRole",
    "UserStatus",
]
