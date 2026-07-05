import unittest

from app.domain import (
    DEFAULT_PRESENTATION_CONTEXT,
    EXCLUDED_API_CAPABILITIES,
    EXCLUDED_PRESENTATION_CONDITION_FIELDS,
    PresentationContext,
)


class PresentationContextTest(unittest.TestCase):
    def test_default_context_is_university_project_for_professor(self) -> None:
        self.assertIs(
            DEFAULT_PRESENTATION_CONTEXT,
            PresentationContext.UNIVERSITY_PROJECT_FOR_PROFESSOR,
        )
        self.assertEqual(
            DEFAULT_PRESENTATION_CONTEXT.value,
            "UNIVERSITY_PROJECT_FOR_PROFESSOR",
        )

    def test_context_is_string_enum_compatible(self) -> None:
        self.assertIsInstance(DEFAULT_PRESENTATION_CONTEXT, str)
        self.assertEqual(str(DEFAULT_PRESENTATION_CONTEXT), "UNIVERSITY_PROJECT_FOR_PROFESSOR")

    def test_custom_presentation_condition_fields_are_excluded(self) -> None:
        self.assertEqual(
            EXCLUDED_PRESENTATION_CONDITION_FIELDS,
            (
                "presentation_target",
                "presentation_purpose",
                "presentation_situation",
                "presentation_context",
                "speech_tone",
            ),
        )

    def test_context_specific_script_transformation_api_is_excluded(self) -> None:
        self.assertIn(
            "presentation_condition_customization",
            EXCLUDED_API_CAPABILITIES,
        )
        self.assertIn(
            "context_specific_script_transformation",
            EXCLUDED_API_CAPABILITIES,
        )


if __name__ == "__main__":
    unittest.main()
