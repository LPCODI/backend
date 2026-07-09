"""Presentation project request and response schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain import DEFAULT_PRESENTATION_CONTEXT, FIXED_PRESENTATION_CONDITION, PresentationContext, PresentationStatus

PresentationTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class PresentationTag(StrEnum):
    """OpenAPI tags used by presentation routers."""

    PRESENTATIONS = "발표 프로젝트"
    PRESENTATION_FILES = "발표 자료"
    SLIDES = "슬라이드"
    ANALYSIS = "발표 자료 분석"
    TIMINGS = "시간 배분"
    SCRIPTS = "발표 대본"


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
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null when provided.")
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


class PresentationFileResponse(BaseModel):
    """Uploaded presentation material metadata returned by file APIs."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    file_id: int
    presentation_id: int
    original_filename: str
    stored_filename: str | None
    file_type: str
    mime_type: str
    file_size_bytes: int
    storage_bucket: str
    object_key: str
    checksum: str | None
    status: str
    slide_count: int | None
    parse_error_message: str | None
    uploaded_at: datetime
    parsed_at: datetime | None


class PresentationParseRequest(BaseModel):
    """Request body for starting material parsing.

    When omitted, the latest uploaded file for the presentation is parsed.
    """

    model_config = ConfigDict(extra="forbid")

    file_id: int | None = Field(default=None, ge=1)


class PresentationParseResponse(BaseModel):
    """Synchronous MVP parse summary returned by the parse endpoint."""

    model_config = ConfigDict(extra="forbid")

    presentation_id: int
    file_id: int
    status: str
    slide_count: int
    parser_provider: str
    parser_version: str
    warnings: list[str] = Field(default_factory=list)


class ParsedSlideResponse(BaseModel):
    """Parsed slide data returned by the parse-result endpoint."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    slide_id: int
    file_id: int
    slide_number: int
    sort_order: int
    title: str | None
    raw_text: str | None
    notes_text: str | None
    image_url: str | None
    image_object_key: str | None
    excluded: bool
    created_at: datetime
    updated_at: datetime


class SlideResponse(ParsedSlideResponse):
    """Slide data returned by slide management APIs."""

    presentation_id: int


class SlideUpdateRequest(BaseModel):
    """Request body for editing parsed slide content."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=300)
    raw_text: str | None = None
    notes_text: str | None = None
    image_url: str | None = None
    image_object_key: str | None = None

    @model_validator(mode="after")
    def at_least_one_field_must_be_provided(self) -> "SlideUpdateRequest":
        """Reject empty slide updates."""

        if not self.model_fields_set:
            raise ValueError("At least one editable slide field must be provided.")
        return self


class SlideOrderUpdateRequest(BaseModel):
    """Request body for replacing the slide display order."""

    model_config = ConfigDict(extra="forbid")

    slide_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def slide_ids_must_be_unique(self) -> "SlideOrderUpdateRequest":
        """Reject duplicate slide ids because order must be unambiguous."""

        if len(self.slide_ids) != len(set(self.slide_ids)):
            raise ValueError("slide_ids must not contain duplicates.")
        return self


class PresentationParseResultResponse(BaseModel):
    """Latest material parsing result for one presentation project."""

    model_config = ConfigDict(extra="forbid")

    presentation_id: int
    file: PresentationFileResponse
    slide_count: int
    slides: list[ParsedSlideResponse] = Field(default_factory=list)


class SlideAnalysisResponse(BaseModel):
    """Slide-level analysis result bound to the latest presentation analysis version."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    slide_analysis_id: int
    presentation_analysis_id: int
    slide_id: int
    importance_score: Decimal | None
    complexity_score: Decimal | None
    core_message: str | None
    missing_explanations: list[Any] | dict[str, Any] | None
    expected_questions: list[Any] | dict[str, Any] | None
    keywords: list[Any] | dict[str, Any] | None
    created_at: datetime


class PresentationAnalysisResponse(BaseModel):
    """Whole-presentation analysis result with versioned slide analyses."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    presentation_analysis_id: int
    presentation_id: int
    version: int
    summary: str | None
    overall_core_message: str | None
    strengths: list[Any] | dict[str, Any] | None
    weaknesses: list[Any] | dict[str, Any] | None
    professor_question_points: list[Any] | dict[str, Any] | None
    model_name: str | None
    prompt_version: str | None
    status: str
    created_at: datetime
    slide_analyses: list[SlideAnalysisResponse] = Field(default_factory=list)


class SlideTimingResponse(BaseModel):
    """Active slide timing allocation returned by timing APIs."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    slide_timing_id: int
    slide_id: int
    version: int
    allocated_seconds: int
    transition_seconds: int
    allocation_reason: str | None
    is_locked: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PresentationTimingResponse(BaseModel):
    """Whole-presentation timing allocation with active slide timings."""

    model_config = ConfigDict(extra="forbid")

    presentation_id: int
    presentation_duration_seconds: int
    total_allocated_seconds: int
    status: str | None
    timings: list[SlideTimingResponse] = Field(default_factory=list)


class SlideTimingUpdateRequest(BaseModel):
    """Request body for manually locking one slide duration."""

    model_config = ConfigDict(extra="forbid")

    allocated_seconds: int = Field(ge=10)


class SlideScriptResponse(BaseModel):
    """Active slide script returned by script APIs."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    slide_script_id: int
    slide_id: int
    previous_slide_script_id: int | None
    edited_by_user_id: int | None
    version: int
    script_text: str
    core_message: str | None
    estimated_seconds: int | None
    emphasis_words: list[Any] | dict[str, Any] | None
    transition_sentence: str | None
    optional_explanation: str | None
    expected_questions: list[Any] | dict[str, Any] | None
    generation_type: str
    revision_reason: str | None
    user_revision_note: str | None
    model_name: str | None
    prompt_version: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PresentationScriptResponse(BaseModel):
    """Whole-presentation script generation result with active slide scripts."""

    model_config = ConfigDict(extra="forbid")

    presentation_id: int
    status: str | None
    scripts: list[SlideScriptResponse] = Field(default_factory=list)


__all__ = [
    "FixedPresentationConditionResponse",
    "ParsedSlideResponse",
    "PresentationCreateRequest",
    "PresentationFileResponse",
    "PresentationAnalysisResponse",
    "PresentationParseRequest",
    "PresentationParseResultResponse",
    "PresentationParseResponse",
    "PresentationResponse",
    "PresentationScriptResponse",
    "PresentationTag",
    "PresentationTitle",
    "PresentationUpdateRequest",
    "SlideOrderUpdateRequest",
    "SlideAnalysisResponse",
    "SlideResponse",
    "SlideScriptResponse",
    "SlideTimingResponse",
    "PresentationTimingResponse",
    "SlideTimingUpdateRequest",
    "SlideUpdateRequest",
]
