"""Presentation material analysis services and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from http import HTTPStatus
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core import ApiError
from app.domain import ErrorCode, PresentationStatus
from app.models import PresentationAnalysis, Slide, SlideAnalysis, User
from app.services.presentations import (
    get_owned_presentation_project,
    validate_presentation_status_transition,
)

ANALYSIS_STATUS_COMPLETED = "COMPLETED"
ANALYSIS_MODEL_NAME = "deterministic-mvp-slide-analysis"
ANALYSIS_PROMPT_VERSION = "0.1.0"
ANALYSIS_NOT_FOUND_MESSAGE = "발표 자료 분석 결과를 찾을 수 없습니다."
ANALYSIS_NOT_READY_MESSAGE = "분석할 슬라이드가 준비되지 않았습니다."
ANALYSIS_INVALID_STATUS_MESSAGE = "현재 발표 상태에서는 자료 분석을 시작할 수 없습니다."
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣]{2,}")
_STOPWORDS = {
    "and",
    "for",
    "the",
    "with",
    "this",
    "that",
    "프로젝트",
    "발표",
    "슬라이드",
    "교수님",
}


@dataclass(frozen=True)
class PresentationAnalysisResult:
    """Created or loaded whole-presentation analysis with ordered slide results."""

    analysis: PresentationAnalysis
    slide_analyses: tuple[SlideAnalysis, ...]


def _next_sqlite_presentation_analysis_id(db: Session) -> int | None:
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(
        select(func.coalesce(func.max(PresentationAnalysis.presentation_analysis_id), 0) + 1)
    ).scalar_one()
    return int(next_id)


def _next_sqlite_slide_analysis_id(db: Session) -> int | None:
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(SlideAnalysis.slide_analysis_id), 0) + 1)).scalar_one()
    return int(next_id)


def _latest_analysis_version(db: Session, *, presentation_id: int) -> int:
    version = db.execute(
        select(func.coalesce(func.max(PresentationAnalysis.version), 0)).where(
            PresentationAnalysis.presentation_id == presentation_id,
        )
    ).scalar_one()
    return int(version)


def _load_analysis_result(db: Session, *, analysis_id: int) -> PresentationAnalysisResult:
    statement = (
        select(PresentationAnalysis)
        .options(selectinload(PresentationAnalysis.slide_analyses).selectinload(SlideAnalysis.slide))
        .where(PresentationAnalysis.presentation_analysis_id == analysis_id)
    )
    analysis = db.execute(statement).scalar_one()
    ordered_slide_analyses = tuple(
        sorted(
            analysis.slide_analyses,
            key=lambda slide_analysis: (
                slide_analysis.slide.sort_order,
                slide_analysis.slide_id,
            ),
        )
    )
    return PresentationAnalysisResult(analysis=analysis, slide_analyses=ordered_slide_analyses)


def _analysis_input_text(slide: Slide) -> str:
    return "\n".join(
        part.strip()
        for part in (slide.title, slide.raw_text, slide.notes_text)
        if isinstance(part, str) and part.strip()
    )


def _keywords_for_text(text: str, *, limit: int = 6) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for token in _TOKEN_PATTERN.findall(text):
        normalized = token.lower()
        if normalized in _STOPWORDS or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _core_message(slide: Slide, keywords: list[str]) -> str:
    if slide.title:
        return f"{slide.slide_number}번 슬라이드는 '{slide.title}'를 중심으로 설명해야 합니다."
    if keywords:
        return f"{slide.slide_number}번 슬라이드는 {', '.join(keywords[:3])}를 중심으로 설명해야 합니다."
    return f"{slide.slide_number}번 슬라이드는 핵심 메시지를 보완해야 합니다."


def _missing_explanations(slide: Slide, text: str) -> list[str]:
    missing: list[str] = []
    if not slide.title:
        missing.append("슬라이드 제목이 없어 핵심 주제가 명확하지 않습니다.")
    if len(text) < 80:
        missing.append("본문 설명이 짧아 교수 평가 관점의 근거와 맥락 보완이 필요합니다.")
    if not slide.notes_text:
        missing.append("발표자 노트가 없어 구두 설명 흐름을 추가하는 것이 좋습니다.")
    return missing


def _expected_questions(slide: Slide, keywords: list[str], missing: list[str]) -> list[dict[str, object]]:
    topic = slide.title or (keywords[0] if keywords else f"{slide.slide_number}번 슬라이드")
    questions = [
        {
            "question": f"{topic}의 핵심 근거는 무엇인가요?",
            "reason": "교수 프로젝트 발표에서 주장과 근거의 연결을 확인할 가능성이 높습니다.",
            "slideId": slide.slide_id,
            "slideNumber": slide.slide_number,
        }
    ]
    if missing:
        questions.append(
            {
                "question": f"{topic}에서 보완해야 할 설명은 무엇인가요?",
                "reason": missing[0],
                "slideId": slide.slide_id,
                "slideNumber": slide.slide_number,
            }
        )
    return questions


def _score_importance(slide: Slide, text: str, slide_count: int) -> Decimal:
    title_weight = Decimal("1.0") if slide.title else Decimal("0.0")
    position_weight = Decimal("1.0") if slide.slide_number in (1, slide_count) else Decimal("0.5")
    text_weight = min(Decimal(len(text)) / Decimal("180"), Decimal("2.0"))
    return min(Decimal("5.0"), Decimal("2.0") + title_weight + position_weight + text_weight).quantize(Decimal("0.01"))


def _score_complexity(text: str, keywords: list[str]) -> Decimal:
    text_weight = min(Decimal(len(text)) / Decimal("220"), Decimal("2.0"))
    keyword_weight = min(Decimal(len(keywords)) / Decimal("3"), Decimal("2.0"))
    return min(Decimal("5.0"), Decimal("1.0") + text_weight + keyword_weight).quantize(Decimal("0.01"))


def _get_analyzable_slides(db: Session, *, presentation_id: int) -> list[Slide]:
    statement = (
        select(Slide)
        .where(
            Slide.presentation_id == presentation_id,
            Slide.excluded.is_(False),
        )
        .order_by(Slide.sort_order.asc(), Slide.slide_id.asc())
    )
    return list(db.execute(statement).scalars().all())


def _ensure_analysis_can_start(current_status: PresentationStatus | str) -> None:
    normalized = current_status if isinstance(current_status, PresentationStatus) else PresentationStatus(current_status)
    if normalized not in {PresentationStatus.PARSED, PresentationStatus.ANALYZED, PresentationStatus.ANALYZING}:
        raise ApiError(
            status_code=HTTPStatus.CONFLICT,
            code=ErrorCode.ANALYSIS_NOT_READY,
            message=ANALYSIS_INVALID_STATUS_MESSAGE,
            details={
                "currentStatus": normalized.value,
                "requiredStatuses": [PresentationStatus.PARSED.value, PresentationStatus.ANALYZED.value],
            },
        )


def analyze_presentation_material(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationAnalysisResult:
    """Create a new deterministic analysis version for parsed, non-excluded slides."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    _ensure_analysis_can_start(presentation.status)
    slides = _get_analyzable_slides(db, presentation_id=presentation.presentation_id)
    if not slides:
        raise ApiError(
            status_code=HTTPStatus.CONFLICT,
            code=ErrorCode.ANALYSIS_NOT_READY,
            message=ANALYSIS_NOT_READY_MESSAGE,
            details={"presentationId": presentation.presentation_id},
        )

    validate_presentation_status_transition(
        current_status=presentation.status,
        next_status=PresentationStatus.ANALYZING,
    )
    presentation.status = PresentationStatus.ANALYZING
    db.flush()

    version = _latest_analysis_version(db, presentation_id=presentation.presentation_id) + 1
    analysis_kwargs: dict[str, object] = {
        "presentation_id": presentation.presentation_id,
        "version": version,
        "summary": f"{len(slides)}개 슬라이드를 교수 대상 대학 프로젝트 발표 관점에서 분석했습니다.",
        "model_name": ANALYSIS_MODEL_NAME,
        "prompt_version": ANALYSIS_PROMPT_VERSION,
        "status": ANALYSIS_STATUS_COMPLETED,
    }
    sqlite_analysis_id = _next_sqlite_presentation_analysis_id(db)
    if sqlite_analysis_id is not None:
        analysis_kwargs["presentation_analysis_id"] = sqlite_analysis_id
    analysis = PresentationAnalysis(**analysis_kwargs)
    db.add(analysis)
    db.flush()

    all_keywords: list[str] = []
    all_missing: list[str] = []
    professor_question_points: list[dict[str, object]] = []
    duplicate_titles: dict[str, int] = {}
    next_slide_analysis_id = _next_sqlite_slide_analysis_id(db)
    for slide in slides:
        text = _analysis_input_text(slide)
        keywords = _keywords_for_text(text)
        missing = _missing_explanations(slide, text)
        questions = _expected_questions(slide, keywords, missing)
        all_keywords.extend(keywords)
        all_missing.extend(missing)
        professor_question_points.extend(questions)
        if slide.title:
            duplicate_titles[slide.title] = duplicate_titles.get(slide.title, 0) + 1

        slide_analysis_kwargs: dict[str, object] = {
            "presentation_analysis_id": analysis.presentation_analysis_id,
            "slide_id": slide.slide_id,
            "importance_score": _score_importance(slide, text, len(slides)),
            "complexity_score": _score_complexity(text, keywords),
            "core_message": _core_message(slide, keywords),
            "missing_explanations": missing,
            "expected_questions": questions,
            "keywords": keywords,
        }
        if next_slide_analysis_id is not None:
            slide_analysis_kwargs["slide_analysis_id"] = next_slide_analysis_id
            next_slide_analysis_id += 1
        db.add(SlideAnalysis(**slide_analysis_kwargs))

    duplicate_title_values = sorted(title for title, count in duplicate_titles.items() if count > 1)
    unique_keywords = list(dict.fromkeys(all_keywords))
    analysis.overall_core_message = (
        f"{presentation.title} 발표는 {', '.join(unique_keywords[:5])}를 중심으로 교수 평가 기준에 맞춰 전달해야 합니다."
        if unique_keywords
        else f"{presentation.title} 발표는 슬라이드별 핵심 메시지를 더 명확히 해야 합니다."
    )
    analysis.strengths = [
        "슬라이드 구조가 발표 흐름에 맞게 정렬되어 있습니다.",
        f"분석 대상 슬라이드가 {len(slides)}개로 확인되었습니다.",
    ]
    analysis.weaknesses = [
        *all_missing[:5],
        *[f"중복 제목 '{title}'가 있어 메시지 차별화가 필요합니다." for title in duplicate_title_values],
    ]
    analysis.professor_question_points = professor_question_points
    validate_presentation_status_transition(
        current_status=presentation.status,
        next_status=PresentationStatus.ANALYZED,
    )
    presentation.status = PresentationStatus.ANALYZED
    db.commit()
    return _load_analysis_result(db, analysis_id=analysis.presentation_analysis_id)


def get_latest_presentation_analysis(
    db: Session,
    *,
    user: User,
    presentation_id: int,
) -> PresentationAnalysisResult:
    """Return the latest completed analysis for an owned presentation."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = (
        select(PresentationAnalysis)
        .where(PresentationAnalysis.presentation_id == presentation.presentation_id)
        .order_by(PresentationAnalysis.version.desc(), PresentationAnalysis.presentation_analysis_id.desc())
    )
    analysis = db.execute(statement).scalars().first()
    if analysis is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.ANALYSIS_NOT_FOUND,
            message=ANALYSIS_NOT_FOUND_MESSAGE,
        )
    return _load_analysis_result(db, analysis_id=analysis.presentation_analysis_id)


def get_latest_slide_analysis(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    slide_id: int,
) -> SlideAnalysis:
    """Return the latest analysis row for one owned slide."""

    latest = get_latest_presentation_analysis(db, user=user, presentation_id=presentation_id)
    for slide_analysis in latest.slide_analyses:
        if slide_analysis.slide_id == slide_id:
            return slide_analysis
    raise ApiError(
        status_code=HTTPStatus.NOT_FOUND,
        code=ErrorCode.ANALYSIS_NOT_FOUND,
        message=ANALYSIS_NOT_FOUND_MESSAGE,
        details={"slideId": slide_id},
    )


__all__ = [
    "ANALYSIS_INVALID_STATUS_MESSAGE",
    "ANALYSIS_MODEL_NAME",
    "ANALYSIS_NOT_FOUND_MESSAGE",
    "ANALYSIS_NOT_READY_MESSAGE",
    "ANALYSIS_PROMPT_VERSION",
    "ANALYSIS_STATUS_COMPLETED",
    "PresentationAnalysisResult",
    "analyze_presentation_material",
    "get_latest_presentation_analysis",
    "get_latest_slide_analysis",
]
