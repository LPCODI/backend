"""Presentation project request and response schemas."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain import DEFAULT_PRESENTATION_CONTEXT, FIXED_PRESENTATION_CONDITION, PresentationContext, PresentationStatus

PresentationTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class PresentationTag(StrEnum):
    """OpenAPI tags used by presentation routers."""

    PRESENTATIONS = "발표 프로젝트"


class FixedPresentationConditionResponse(BaseModel):
    """Server-fixed presentation condition returned to API clients."""

    model_config = ConfigDict(extra="forbid")

    presentation_context: PresentationContext = DEFAULT_PRESENTATION_CONTEXT
    presentation_target: str = FIXED_PRESENTATION_CONDITION["presentation_target"]
    presentation_purpose: str = FIXED_PRESENTATION_CONDITION["presentation_purpose"]
    presentation_situation: str = FIXED_PRESENTATION_CONDITION["presentation_situation"]
    speech_tone: str = FIXED_PRESENTATION_CONDITION["speech_tone"]


class PresentationCreateRequest(BaseModel):
    """Request body for creating a professor-facing university project presentation."""

    model_config = ConfigDict(extra="forbid")

    title: PresentationTitle
    total_duration_seconds: int = Field(ge=120, le=7200)
    qa_duration_seconds: int = Field(ge=0)


class PresentationUpdateRequest(BaseModel):
    """Request body for updating editable presentation project fields."""

    model_config = ConfigDict(extra="forbid")

    title: PresentationTitle | None = None
    total_duration_seconds: int | None = Field(default=None, ge=120, le=7200)
    qa_duration_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field_must_be_provided(self) -> "PresentationUpdateRequest":
        """Reject empty updates while keeping fixed condition fields non-editable."""

        if not self.model_fields_set:
            raise ValueError("At least one editable presentation field must be provided.")
        return self


class PresentationResponse(BaseModel):
    """Presentation project data returned by presentation APIs."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    presentation_id: int
    title: str
    total_duration_seconds: int
    qa_duration_seconds: int
    presentation_duration_seconds: int
    presentation_context: PresentationContext = DEFAULT_PRESENTATION_CONTEXT
    status: PresentationStatus
    fixed_condition: FixedPresentationConditionResponse = Field(default_factory=FixedPresentationConditionResponse)
    created_at: datetime
    updated_at: datetime


__all__ = [
    "FixedPresentationConditionResponse",
    "PresentationCreateRequest",
    "PresentationResponse",
    "PresentationTag",
    "PresentationTitle",
    "PresentationUpdateRequest",
]
