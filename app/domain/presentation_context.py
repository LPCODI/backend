"""Presentation context values fixed by the product specification."""

from enum import StrEnum


class PresentationContext(StrEnum):
    UNIVERSITY_PROJECT_FOR_PROFESSOR = "UNIVERSITY_PROJECT_FOR_PROFESSOR"


DEFAULT_PRESENTATION_CONTEXT = PresentationContext.UNIVERSITY_PROJECT_FOR_PROFESSOR

# These presentation condition fields are intentionally excluded from public
# request schemas. The product fixes them to DEFAULT_PRESENTATION_CONTEXT.
EXCLUDED_PRESENTATION_CONDITION_FIELDS = (
    "presentation_target",
    "presentation_purpose",
    "presentation_context",
    "speech_tone",
)

# Do not add endpoints for these capabilities unless the product scope changes.
EXCLUDED_API_CAPABILITIES = (
    "presentation_condition_customization",
    "context_specific_script_transformation",
)
