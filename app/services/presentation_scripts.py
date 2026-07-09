"""Deterministic professor-facing slide script generation."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
import re
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import ApiError
from app.domain import ErrorCode
from app.models import Presentation, Slide, SlideAnalysis, SlideScript, SlideTiming, User
from app.services.presentation_script_prompts import SCRIPT_PROMPT_VERSION
from app.services.presentations import get_owned_presentation_project
from app.services.slides import get_owned_slide

SCRIPT_GENERATION_MODEL_NAME = "deterministic-mvp-professor-script"
SCRIPT_GENERATION_TYPE_AI = "AI"
SCRIPT_GENERATION_TYPE_USER_EDIT = "USER_EDIT"
SCRIPT_STATUS_COMPLETED = "COMPLETED"
SCRIPT_NOT_FOUND_MESSAGE = "발표 대본을 찾을 수 없습니다."
SCRIPT_NOT_READY_MESSAGE = "대본을 생성할 슬라이드가 준비되지 않았습니다."
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣]{2,}")


@dataclass(frozen=True, slots=True)
class SlideScriptDraft:
    """Generated script draft for one slide before versioned persistence."""

    slide_id: int
    slide_number: int
    script_text: str
    core_message: str
    estimated_seconds: int
    emphasis_words: tuple[str, ...]
    transition_sentence: str
    optional_explanation: str | None
    expected_questions: tuple[dict[str, str], ...]
    generation_type: str = SCRIPT_GENERATION_TYPE_AI
    model_name: str = SCRIPT_GENERATION_MODEL_NAME
    prompt_version: str = SCRIPT_PROMPT_VERSION


@dataclass(frozen=True, slots=True)
class PresentationScriptDraftResult:
    """Generated script drafts for an owned presentation."""

    presentation: Presentation
    scripts: tuple[SlideScriptDraft, ...]


@dataclass(frozen=True, slots=True)
class PresentationScriptPersistenceResult:
    """Persisted active scripts for an owned presentation."""

    presentation: Presentation
    scripts: tuple[SlideScript, ...]


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


def _string_items(value: object, *, limit: int = 5) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for item in _json_sequence(value):
        if isinstance(item, str):
            text = _plain_text(item)
        elif isinstance(item, dict):
            text = _plain_text(item.get("keyword") or item.get("text") or item.get("message"))
        else:
            text = _plain_text(str(item))
        normalized = text.lower()
        if text and normalized not in seen:
            seen.add(normalized)
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _keywords_from_slide(slide: Slide, *, limit: int = 5) -> list[str]:
    text = " ".join(part for part in (_plain_text(slide.title), _plain_text(slide.raw_text)) if part)
    keywords: list[str] = []
    seen: set[str] = set()
    for token in _TOKEN_PATTERN.findall(text):
        normalized = token.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _question_items(value: object, *, limit: int = 3) -> tuple[dict[str, str], ...]:
    questions: list[dict[str, str]] = []
    for item in _json_sequence(value):
        if isinstance(item, dict):
            question = _plain_text(item.get("question"))
            hint = _plain_text(item.get("answer_hint") or item.get("reason") or item.get("intent"))
        else:
            question = _plain_text(str(item))
            hint = ""
        if question:
            questions.append({"question": question, "answer_hint": hint})
        if len(questions) >= limit:
            break
    return tuple(questions)


def _first_sentence(text: str, *, max_chars: int = 120) -> str:
    text = _plain_text(text)
    if not text:
        return ""
    for separator in (".", "?", "!", "。", "？", "！"):
        if separator in text:
            candidate = text.split(separator, 1)[0].strip()
            if candidate:
                return candidate[:max_chars]
    return text[:max_chars]


def _fallback_core_message(slide: Slide, keywords: list[str]) -> str:
    title = _plain_text(slide.title)
    if title:
        return f"{slide.slide_number}번 슬라이드는 '{title}'의 핵심 내용을 교수님께 명확히 설명합니다."
    if keywords:
        return f"{slide.slide_number}번 슬라이드는 {', '.join(keywords[:3])}를 중심으로 설명합니다."
    return f"{slide.slide_number}번 슬라이드는 프로젝트의 핵심 흐름을 보완해 설명합니다."


def _transition_sentence(current: Slide, next_slide: Slide | None) -> str:
    if next_slide is None:
        return "이 내용까지 정리한 뒤 전체 발표의 핵심 결론으로 마무리하겠습니다."
    next_title = _plain_text(next_slide.title) or f"{next_slide.slide_number}번 슬라이드"
    current_title = _plain_text(current.title) or f"{current.slide_number}번 슬라이드"
    return f"{current_title}의 내용을 바탕으로 다음 슬라이드에서는 {next_title}를 이어서 설명하겠습니다."


def _script_text(
    *,
    slide: Slide,
    core_message: str,
    emphasis_words: list[str],
    timing: SlideTiming | None,
    transition_sentence: str,
) -> str:
    title = _plain_text(slide.title) or f"{slide.slide_number}번 슬라이드"
    body_summary = _first_sentence(_plain_text(slide.raw_text))
    notes_summary = _first_sentence(_plain_text(slide.notes_text), max_chars=100)
    estimated_seconds = timing.allocated_seconds if timing else 90
    parts = [
        f"교수님, 이번 {slide.slide_number}번 슬라이드에서는 {title}를 설명드리겠습니다.",
        core_message,
    ]
    if body_summary:
        parts.append(f"자료의 핵심 근거는 {body_summary}입니다.")
    if notes_summary:
        parts.append(f"발표에서는 {notes_summary}라는 흐름으로 보충하겠습니다.")
    if emphasis_words:
        parts.append(f"특히 {', '.join(emphasis_words[:3])}를 강조해서 보시면 됩니다.")
    parts.append(f"이 슬라이드는 약 {estimated_seconds}초 안에 설명하겠습니다.")
    parts.append(transition_sentence)
    return " ".join(parts)


def generate_slide_script_drafts(
    *,
    presentation: Presentation,
    slides: Iterable[Slide],
    timings_by_slide_id: dict[int, SlideTiming] | None = None,
    analyses_by_slide_id: dict[int, SlideAnalysis] | None = None,
) -> tuple[SlideScriptDraft, ...]:
    """Generate deterministic script drafts for non-excluded slides."""

    ordered_slides = sorted(
        (slide for slide in slides if not slide.excluded),
        key=lambda item: (item.sort_order, item.slide_id),
    )
    if not ordered_slides:
        raise ApiError(
            status_code=HTTPStatus.CONFLICT,
            code=ErrorCode.SCRIPT_NOT_READY,
            message=SCRIPT_NOT_READY_MESSAGE,
            details={"presentationId": presentation.presentation_id},
        )

    timings_by_slide_id = timings_by_slide_id or {}
    analyses_by_slide_id = analyses_by_slide_id or {}
    drafts: list[SlideScriptDraft] = []
    for index, slide in enumerate(ordered_slides):
        analysis = analyses_by_slide_id.get(slide.slide_id)
        timing = timings_by_slide_id.get(slide.slide_id)
        keywords = _string_items(analysis.keywords if analysis else None)
        if not keywords:
            keywords = _keywords_from_slide(slide)
        core_message = _plain_text(analysis.core_message) if analysis else ""
        if not core_message:
            core_message = _fallback_core_message(slide, keywords)
        transition = _transition_sentence(
            slide,
            ordered_slides[index + 1] if index + 1 < len(ordered_slides) else None,
        )
        missing = _string_items(analysis.missing_explanations if analysis else None, limit=3)
        drafts.append(
            SlideScriptDraft(
                slide_id=slide.slide_id,
                slide_number=slide.slide_number,
                script_text=_script_text(
                    slide=slide,
                    core_message=core_message,
                    emphasis_words=keywords,
                    timing=timing,
                    transition_sentence=transition,
                ),
                core_message=core_message,
                estimated_seconds=timing.allocated_seconds if timing else 90,
                emphasis_words=tuple(keywords),
                transition_sentence=transition,
                optional_explanation=" ".join(missing) if missing else None,
                expected_questions=_question_items(analysis.expected_questions if analysis else None),
            )
        )
    return tuple(drafts)


def _active_slides(db: Session, *, presentation_id: int) -> list[Slide]:
    statement = (
        select(Slide)
        .where(
            Slide.presentation_id == presentation_id,
            Slide.excluded.is_(False),
        )
        .order_by(Slide.sort_order.asc(), Slide.slide_id.asc())
    )
    return list(db.execute(statement).scalars().all())


def _active_timings_by_slide_id(db: Session, *, presentation_id: int) -> dict[int, SlideTiming]:
    statement = (
        select(SlideTiming)
        .join(Slide, Slide.slide_id == SlideTiming.slide_id)
        .where(
            Slide.presentation_id == presentation_id,
            SlideTiming.is_active.is_(True),
        )
    )
    return {timing.slide_id: timing for timing in db.execute(statement).scalars().all()}


def _next_sqlite_slide_script_id(db: Session) -> int | None:
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(SlideScript.slide_script_id), 0) + 1)).scalar_one()
    return int(next_id)


def _latest_analyses_by_slide_id(db: Session, *, presentation_id: int) -> dict[int, SlideAnalysis]:
    latest_analysis_id = db.execute(
        select(SlideAnalysis.presentation_analysis_id)
        .join(Slide, Slide.slide_id == SlideAnalysis.slide_id)
        .where(Slide.presentation_id == presentation_id)
        .order_by(SlideAnalysis.presentation_analysis_id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_analysis_id is None:
        return {}
    statement = select(SlideAnalysis).where(SlideAnalysis.presentation_analysis_id == latest_analysis_id)
    return {analysis.slide_id: analysis for analysis in db.execute(statement).scalars().all()}


def _latest_script_version(db: Session, *, slide_id: int) -> int:
    version = db.execute(
        select(func.coalesce(func.max(SlideScript.version), 0)).where(SlideScript.slide_id == slide_id)
    ).scalar_one()
    return int(version)


def _active_scripts(db: Session, *, presentation_id: int) -> list[SlideScript]:
    statement = (
        select(SlideScript)
        .join(Slide, Slide.slide_id == SlideScript.slide_id)
        .where(
            Slide.presentation_id == presentation_id,
            SlideScript.is_active.is_(True),
        )
        .order_by(Slide.sort_order.asc(), Slide.slide_id.asc())
    )
    return list(db.execute(statement).scalars().all())


def _active_scripts_by_slide_id(db: Session, *, presentation_id: int) -> dict[int, SlideScript]:
    return {script.slide_id: script for script in _active_scripts(db, presentation_id=presentation_id)}


def generate_presentation_script_drafts(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationScriptDraftResult:
    """Generate script drafts for an owned presentation without persisting versions yet."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    scripts = generate_slide_script_drafts(
        presentation=presentation,
        slides=_active_slides(db, presentation_id=presentation.presentation_id),
        timings_by_slide_id=_active_timings_by_slide_id(db, presentation_id=presentation.presentation_id),
        analyses_by_slide_id=_latest_analyses_by_slide_id(db, presentation_id=presentation.presentation_id),
    )
    return PresentationScriptDraftResult(presentation=presentation, scripts=scripts)


def persist_presentation_script_drafts(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationScriptPersistenceResult:
    """Generate script drafts and persist them as the next active version per slide."""

    draft_result = generate_presentation_script_drafts(db, user=user, presentation_id=presentation_id)
    presentation = draft_result.presentation
    previous_active_by_slide_id = _active_scripts_by_slide_id(db, presentation_id=presentation.presentation_id)
    next_script_id = _next_sqlite_slide_script_id(db)
    scripts: list[SlideScript] = []

    for previous in previous_active_by_slide_id.values():
        previous.is_active = False

    for draft in draft_result.scripts:
        script_kwargs: dict[str, object] = {
            "slide_id": draft.slide_id,
            "previous_slide_script_id": (
                previous_active_by_slide_id[draft.slide_id].slide_script_id
                if draft.slide_id in previous_active_by_slide_id
                else None
            ),
            "version": _latest_script_version(db, slide_id=draft.slide_id) + 1,
            "script_text": draft.script_text,
            "core_message": draft.core_message,
            "estimated_seconds": draft.estimated_seconds,
            "emphasis_words": list(draft.emphasis_words),
            "transition_sentence": draft.transition_sentence,
            "optional_explanation": draft.optional_explanation,
            "expected_questions": list(draft.expected_questions),
            "generation_type": draft.generation_type,
            "revision_reason": "교수 발표용 대본 자동 생성",
            "model_name": draft.model_name,
            "prompt_version": draft.prompt_version,
            "is_active": True,
        }
        if next_script_id is not None:
            script_kwargs["slide_script_id"] = next_script_id
            next_script_id += 1
        script = SlideScript(**script_kwargs)
        db.add(script)
        scripts.append(script)

    presentation.script_status = SCRIPT_STATUS_COMPLETED
    db.commit()
    return get_latest_presentation_scripts(db, user_id=presentation.user_id, presentation_id=presentation.presentation_id)


def get_latest_presentation_scripts(
    db: Session,
    *,
    user: User | None = None,
    user_id: int | None = None,
    presentation_id: int,
) -> PresentationScriptPersistenceResult:
    """Return active scripts for one owned presentation."""

    if user is not None:
        presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    else:
        presentation = db.get(Presentation, presentation_id)
        if presentation is None or presentation.user_id != user_id or presentation.deleted_at is not None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code=ErrorCode.PRESENTATION_NOT_FOUND,
                message="발표 프로젝트를 찾을 수 없습니다.",
            )
    scripts = _active_scripts(db, presentation_id=presentation.presentation_id)
    if not scripts:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.SCRIPT_NOT_FOUND,
            message=SCRIPT_NOT_FOUND_MESSAGE,
        )
    return PresentationScriptPersistenceResult(presentation=presentation, scripts=tuple(scripts))


def create_user_edited_slide_script(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    slide_id: int,
    script_text: str,
    user_revision_note: str | None = None,
) -> SlideScript:
    """Persist a user-edited slide script as a new active version."""

    normalized_script_text = " ".join(script_text.split())
    if not normalized_script_text:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="대본 내용은 비워둘 수 없습니다.",
            details={"field": "scriptText"},
        )
    slide = get_owned_slide(db, user=user, presentation_id=presentation_id, slide_id=slide_id)
    previous = _active_scripts_by_slide_id(db, presentation_id=presentation_id).get(slide.slide_id)
    if previous is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.SCRIPT_NOT_FOUND,
            message=SCRIPT_NOT_FOUND_MESSAGE,
        )

    previous.is_active = False
    script_kwargs: dict[str, object] = {
        "slide_id": slide.slide_id,
        "previous_slide_script_id": previous.slide_script_id,
        "edited_by_user_id": user.user_id,
        "version": _latest_script_version(db, slide_id=slide.slide_id) + 1,
        "script_text": normalized_script_text,
        "core_message": previous.core_message,
        "estimated_seconds": previous.estimated_seconds,
        "emphasis_words": previous.emphasis_words,
        "transition_sentence": previous.transition_sentence,
        "optional_explanation": previous.optional_explanation,
        "expected_questions": previous.expected_questions,
        "generation_type": SCRIPT_GENERATION_TYPE_USER_EDIT,
        "revision_reason": "사용자 직접 수정",
        "user_revision_note": " ".join(user_revision_note.split()) if user_revision_note else None,
        "model_name": previous.model_name,
        "prompt_version": previous.prompt_version,
        "is_active": True,
    }
    next_script_id = _next_sqlite_slide_script_id(db)
    if next_script_id is not None:
        script_kwargs["slide_script_id"] = next_script_id
    script = SlideScript(**script_kwargs)
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


__all__ = [
    "PresentationScriptDraftResult",
    "PresentationScriptPersistenceResult",
    "SCRIPT_GENERATION_MODEL_NAME",
    "SCRIPT_GENERATION_TYPE_AI",
    "SCRIPT_GENERATION_TYPE_USER_EDIT",
    "SCRIPT_NOT_FOUND_MESSAGE",
    "SCRIPT_NOT_READY_MESSAGE",
    "SCRIPT_STATUS_COMPLETED",
    "SlideScriptDraft",
    "create_user_edited_slide_script",
    "get_latest_presentation_scripts",
    "generate_presentation_script_drafts",
    "generate_slide_script_drafts",
    "persist_presentation_script_drafts",
]
