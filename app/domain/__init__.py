"""Domain constants and types."""

from app.domain.error_codes import ERROR_CODES_BY_DOMAIN, ErrorCode, ErrorDomain
from app.domain.accounts import DEFAULT_USER_ROLE, DEFAULT_USER_STATUS, UserRole, UserStatus
from app.domain.presentation_context import (
    DEFAULT_PRESENTATION_CONTEXT,
    EXCLUDED_API_CAPABILITIES,
    EXCLUDED_PRESENTATION_CONDITION_FIELDS,
    FIXED_PRESENTATION_CONDITION,
    PresentationContext,
)
from app.domain.statuses import AgentType, JobStatus, PresentationStatus, RehearsalStatus

__all__ = [
    "AgentType",
    "DEFAULT_PRESENTATION_CONTEXT",
    "DEFAULT_USER_ROLE",
    "DEFAULT_USER_STATUS",
    "ERROR_CODES_BY_DOMAIN",
    "EXCLUDED_API_CAPABILITIES",
    "EXCLUDED_PRESENTATION_CONDITION_FIELDS",
    "FIXED_PRESENTATION_CONDITION",
    "ErrorCode",
    "ErrorDomain",
    "JobStatus",
    "PresentationContext",
    "PresentationStatus",
    "RehearsalStatus",
    "UserRole",
    "UserStatus",
]
