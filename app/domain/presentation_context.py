"""Presentation context values fixed by the product specification."""

from enum import StrEnum
from types import MappingProxyType


class PresentationContext(StrEnum):
    UNIVERSITY_PROJECT_FOR_PROFESSOR = "UNIVERSITY_PROJECT_FOR_PROFESSOR"


DEFAULT_PRESENTATION_CONTEXT = PresentationContext.UNIVERSITY_PROJECT_FOR_PROFESSOR

FIXED_PRESENTATION_CONDITION = MappingProxyType(
    {
        "presentation_context": DEFAULT_PRESENTATION_CONTEXT.value,
        "presentation_target": "담당 교수님",
        "presentation_purpose": "대학 프로젝트 발표 및 평가",
        "presentation_situation": "강의실 또는 프로젝트 발표 자리",
        "speech_tone": "공식적이고 이해하기 쉬운 설명체",
    }
)

# These presentation condition fields are intentionally excluded from public
# request schemas. The product fixes them to DEFAULT_PRESENTATION_CONTEXT.
EXCLUDED_PRESENTATION_CONDITION_FIELDS = (
    "presentation_target",
    "presentation_purpose",
    "presentation_situation",
    "presentation_context",
    "speech_tone",
)

# Do not add endpoints for these capabilities unless the product scope changes.
EXCLUDED_API_CAPABILITIES = (
    "presentation_condition_customization",
    "context_specific_script_transformation",
)
