"""Prompt builders for professor-facing presentation scripts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from app.domain import DEFAULT_PRESENTATION_CONTEXT, FIXED_PRESENTATION_CONDITION, PresentationContext
from app.models import Presentation, Slide, SlideAnalysis, SlideTiming

SCRIPT_PROMPT_VERSION = "professor-script-v1"

SCRIPT_RESPONSE_SCHEMA: dict[str, object] = {
    "slide_id": "integer",
    "slide_number": "integer",
    "script_text": "string",
    "core_message": "string",
    "estimated_seconds": "integer",
    "emphasis_words": ["string"],
    "transition_sentence": "string",
    "optional_explanation": "string",
    "expected_questions": [
        {
            "question": "string",
            "answer_hint": "string",
        }
    ],
}


@dataclass(frozen=True, slots=True)
class ProfessorScriptPrompt:
    """Complete prompt payload for generating one slide script."""

    prompt_version: str
    presentation_context: PresentationContext
    system_prompt: str
    user_prompt: str
    response_schema: dict[str, object]


def _plain_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _json_sequence(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    return [value]


def _string_items(value: object, *, limit: int = 6) -> list[str]:
    items: list[str] = []
    for item in _json_sequence(value):
        if isinstance(item, str):
            text = _plain_text(item)
        elif isinstance(item, dict):
            text = _plain_text(item.get("keyword") or item.get("text") or item.get("message"))
        else:
            text = _plain_text(str(item))
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _question_items(value: object, *, limit: int = 5) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for item in _json_sequence(value):
        if isinstance(item, dict):
            question = _plain_text(item.get("question"))
            reason = _plain_text(item.get("reason") or item.get("answer_hint") or item.get("intent"))
        else:
            question = _plain_text(str(item))
            reason = ""
        if question:
            questions.append({"question": question, "answer_hint": reason})
        if len(questions) >= limit:
            break
    return questions


def _slide_payload(
    *,
    presentation: Presentation,
    slide: Slide,
    timing: SlideTiming | None,
    analysis: SlideAnalysis | None,
    previous_slide: Slide | None,
    next_slide: Slide | None,
    feedback: str | None,
) -> dict[str, object]:
    return {
        "presentation": {
            "presentation_id": presentation.presentation_id,
            "title": presentation.title,
            "presentation_duration_seconds": presentation.presentation_duration_seconds,
            "fixed_condition": dict(FIXED_PRESENTATION_CONDITION),
        },
        "slide": {
            "slide_id": slide.slide_id,
            "slide_number": slide.slide_number,
            "title": _plain_text(slide.title),
            "raw_text": _plain_text(slide.raw_text),
            "notes_text": _plain_text(slide.notes_text),
            "previous_title": _plain_text(previous_slide.title) if previous_slide else "",
            "next_title": _plain_text(next_slide.title) if next_slide else "",
        },
        "timing": {
            "allocated_seconds": timing.allocated_seconds if timing else None,
            "transition_seconds": timing.transition_seconds if timing else None,
        },
        "analysis": {
            "core_message": _plain_text(analysis.core_message) if analysis else "",
            "keywords": _string_items(analysis.keywords if analysis else None),
            "missing_explanations": _string_items(analysis.missing_explanations if analysis else None),
            "expected_questions": _question_items(analysis.expected_questions if analysis else None),
        },
        "user_feedback": _plain_text(feedback),
    }


def _build_system_prompt() -> str:
    return "\n".join(
        (
            "당신은 대학 프로젝트를 담당 교수님 앞에서 발표하는 학생을 돕는 발표 대본 작성자입니다.",
            "발표 대상, 목적, 상황, 말투는 시스템 고정 조건만 사용하고 임의로 바꾸지 않습니다.",
            "공식적이고 이해하기 쉬운 설명체로 작성하되, 교수 평가 관점에서 근거와 한계를 명확히 설명합니다.",
            "슬라이드 원문에 없는 사실은 단정하지 말고, 필요한 보완 설명은 optional_explanation에 분리합니다.",
            "반드시 요청된 JSON 스키마에 맞춰 한 슬라이드의 대본만 반환합니다.",
        )
    )


def _build_user_prompt(payload: dict[str, object]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    schema_json = json.dumps(SCRIPT_RESPONSE_SCHEMA, ensure_ascii=False, sort_keys=True, indent=2)
    return "\n".join(
        (
            "다음 발표 프로젝트와 슬라이드 정보를 바탕으로 교수 발표용 슬라이드 대본을 작성하세요.",
            "",
            "작성 규칙:",
            "- allocated_seconds가 있으면 해당 시간 안에 말할 수 있는 분량으로 작성합니다.",
            "- 핵심 메시지, 강조 단어, 다음 슬라이드 전환 문장을 포함합니다.",
            "- 예상 교수 질문은 대본 뒤에 대비할 수 있도록 answer_hint와 함께 정리합니다.",
            "- missing_explanations는 optional_explanation에 반영하되 본문 대본을 장황하게 만들지 않습니다.",
            "",
            "입력:",
            payload_json,
            "",
            "응답 JSON 스키마:",
            schema_json,
        )
    )


def build_professor_script_prompt(
    *,
    presentation: Presentation,
    slide: Slide,
    timing: SlideTiming | None = None,
    analysis: SlideAnalysis | None = None,
    previous_slide: Slide | None = None,
    next_slide: Slide | None = None,
    feedback: str | None = None,
) -> ProfessorScriptPrompt:
    """Build a deterministic prompt for one professor-facing slide script."""

    context = presentation.presentation_context or DEFAULT_PRESENTATION_CONTEXT
    if not isinstance(context, PresentationContext):
        context = PresentationContext(context)
    payload = _slide_payload(
        presentation=presentation,
        slide=slide,
        timing=timing,
        analysis=analysis,
        previous_slide=previous_slide,
        next_slide=next_slide,
        feedback=feedback,
    )
    return ProfessorScriptPrompt(
        prompt_version=SCRIPT_PROMPT_VERSION,
        presentation_context=context,
        system_prompt=_build_system_prompt(),
        user_prompt=_build_user_prompt(payload),
        response_schema=dict(SCRIPT_RESPONSE_SCHEMA),
    )


def build_professor_script_prompts(
    *,
    presentation: Presentation,
    slides: Iterable[Slide],
    timings_by_slide_id: dict[int, SlideTiming] | None = None,
    analyses_by_slide_id: dict[int, SlideAnalysis] | None = None,
    feedback_by_slide_id: dict[int, str] | None = None,
) -> tuple[ProfessorScriptPrompt, ...]:
    """Build ordered prompts for every supplied non-excluded slide."""

    ordered_slides = sorted(
        (slide for slide in slides if not slide.excluded),
        key=lambda item: (item.sort_order, item.slide_id),
    )
    timings_by_slide_id = timings_by_slide_id or {}
    analyses_by_slide_id = analyses_by_slide_id or {}
    feedback_by_slide_id = feedback_by_slide_id or {}
    prompts: list[ProfessorScriptPrompt] = []
    for index, slide in enumerate(ordered_slides):
        previous_slide = ordered_slides[index - 1] if index > 0 else None
        next_slide = ordered_slides[index + 1] if index + 1 < len(ordered_slides) else None
        prompts.append(
            build_professor_script_prompt(
                presentation=presentation,
                slide=slide,
                timing=timings_by_slide_id.get(slide.slide_id),
                analysis=analyses_by_slide_id.get(slide.slide_id),
                previous_slide=previous_slide,
                next_slide=next_slide,
                feedback=feedback_by_slide_id.get(slide.slide_id),
            )
        )
    return tuple(prompts)


__all__ = [
    "ProfessorScriptPrompt",
    "SCRIPT_PROMPT_VERSION",
    "SCRIPT_RESPONSE_SCHEMA",
    "build_professor_script_prompt",
    "build_professor_script_prompts",
]
