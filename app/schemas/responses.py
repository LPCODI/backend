"""Common API response schemas."""

from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


DataT = TypeVar("DataT")
DEFAULT_SUCCESS_MESSAGE = "요청이 정상적으로 처리되었습니다."
DEFAULT_ERROR_MESSAGE = "요청을 처리할 수 없습니다."
FAILURE_RESPONSE_FIELDS = ("success", "error", "timestamp")
ERROR_PAYLOAD_FIELDS = ("code", "message", "details")


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for response payloads."""

    return datetime.now(timezone.utc)


class SuccessResponse(BaseModel, Generic[DataT]):
    """Standard success response wrapper used by API endpoints."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DataT
    message: str = DEFAULT_SUCCESS_MESSAGE
    timestamp: datetime = Field(default_factory=utc_now)


class ErrorPayload(BaseModel):
    """Standard error object embedded in failed API responses."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = DEFAULT_ERROR_MESSAGE
    details: Any | None = None


class FailureResponse(BaseModel):
    """Standard failure response wrapper used by API endpoints."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[False] = False
    error: ErrorPayload
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = [
    "DEFAULT_ERROR_MESSAGE",
    "DEFAULT_SUCCESS_MESSAGE",
    "ERROR_PAYLOAD_FIELDS",
    "ErrorPayload",
    "FAILURE_RESPONSE_FIELDS",
    "FailureResponse",
    "SuccessResponse",
    "utc_now",
]
