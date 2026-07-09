import json
import unittest
from decimal import Decimal

from app.domain import DEFAULT_PRESENTATION_CONTEXT
from app.models import Presentation, Slide, SlideAnalysis, SlideTiming
from app.services import (
    SCRIPT_PROMPT_VERSION,
    build_professor_script_prompt,
    build_professor_script_prompts,
)


class PresentationScriptPromptBuilderTest(unittest.TestCase):
    def _presentation(self) -> Presentation:
        return Presentation(
            presentation_id=1,
            user_id=1,
            title="AI Speech Backend",
            total_duration_seconds=600,
            qa_duration_seconds=120,
            presentation_duration_seconds=480,
        )

    def _slide(self, slide_id: int, slide_number: int, sort_order: int, title: str, *, excluded: bool = False) -> Slide:
        return Slide(
            slide_id=slide_id,
            presentation_id=1,
            file_id=1,
            slide_number=slide_number,
            sort_order=sort_order,
            title=title,
            raw_text="FastAPI 서버가 발표 자료 분석과 리허설 피드백 흐름을 관리합니다.",
            notes_text="교수님께 구조와 책임 분리를 중심으로 설명합니다.",
            excluded=excluded,
        )

    def test_prompt_uses_fixed_professor_presentation_condition(self) -> None:
        presentation = self._presentation()
        slide = self._slide(10, 2, 2, "Backend Architecture")
        timing = SlideTiming(
            slide_timing_id=1,
            slide_id=slide.slide_id,
            version=1,
            allocated_seconds=180,
            transition_seconds=5,
            allocation_reason="자동 배분",
        )
        analysis = SlideAnalysis(
            slide_analysis_id=1,
            presentation_analysis_id=1,
            slide_id=slide.slide_id,
            importance_score=Decimal("4.20"),
            complexity_score=Decimal("3.50"),
            core_message="백엔드가 AI 분석 흐름을 안정적으로 중계한다는 점을 설명해야 합니다.",
            keywords=["FastAPI", "SQLAlchemy", "Redis"],
            missing_explanations=["장애 대응 흐름 설명이 부족합니다."],
            expected_questions=[
                {
                    "question": "Redis 큐가 필요한 이유는 무엇인가요?",
                    "reason": "오래 걸리는 AI 분석 작업 분리를 확인할 수 있습니다.",
                }
            ],
        )

        prompt = build_professor_script_prompt(
            presentation=presentation,
            slide=slide,
            timing=timing,
            analysis=analysis,
            previous_slide=self._slide(9, 1, 1, "Problem"),
            next_slide=self._slide(11, 3, 3, "Demo"),
            feedback="근거를 더 짧게 말하고 전환 문장을 분명히 해주세요.",
        )

        self.assertEqual(prompt.prompt_version, SCRIPT_PROMPT_VERSION)
        self.assertEqual(prompt.presentation_context, DEFAULT_PRESENTATION_CONTEXT)
        self.assertIn("담당 교수님", prompt.user_prompt)
        self.assertIn("대학 프로젝트 발표 및 평가", prompt.user_prompt)
        self.assertIn("공식적이고 이해하기 쉬운 설명체", prompt.user_prompt)
        self.assertIn("allocated_seconds", prompt.user_prompt)
        self.assertIn("180", prompt.user_prompt)
        self.assertIn("Redis 큐가 필요한 이유", prompt.user_prompt)
        self.assertIn("optional_explanation", prompt.user_prompt)
        self.assertIn("JSON 스키마", prompt.user_prompt)
        self.assertEqual(prompt.response_schema["slide_id"], "integer")

    def test_prompt_contains_valid_json_payload_and_schema_sections(self) -> None:
        prompt = build_professor_script_prompt(
            presentation=self._presentation(),
            slide=self._slide(10, 2, 2, "Backend Architecture"),
        )
        input_json = prompt.user_prompt.split("입력:\n", 1)[1].split("\n\n응답 JSON 스키마:\n", 1)[0]
        schema_json = prompt.user_prompt.split("응답 JSON 스키마:\n", 1)[1]

        payload = json.loads(input_json)
        schema = json.loads(schema_json)

        self.assertEqual(payload["presentation"]["fixed_condition"]["presentation_context"], "UNIVERSITY_PROJECT_FOR_PROFESSOR")
        self.assertEqual(payload["slide"]["title"], "Backend Architecture")
        self.assertIsNone(payload["timing"]["allocated_seconds"])
        self.assertEqual(schema["script_text"], "string")

    def test_batch_prompt_builder_orders_and_skips_excluded_slides(self) -> None:
        presentation = self._presentation()
        first = self._slide(10, 1, 1, "Opening")
        excluded = self._slide(11, 2, 2, "Appendix", excluded=True)
        second = self._slide(12, 3, 3, "Result")

        prompts = build_professor_script_prompts(
            presentation=presentation,
            slides=[second, excluded, first],
        )

        self.assertEqual(len(prompts), 2)
        self.assertIn('"slide_number": 1', prompts[0].user_prompt)
        self.assertIn('"next_title": "Result"', prompts[0].user_prompt)
        self.assertIn('"previous_title": "Opening"', prompts[1].user_prompt)
        self.assertNotIn("Appendix", "\n".join(prompt.user_prompt for prompt in prompts))


if __name__ == "__main__":
    unittest.main()
