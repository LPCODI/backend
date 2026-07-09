"""Slide timing allocation services."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from http import HTTPStatus

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core import ApiError
from app.domain import ErrorCode
from app.models import Presentation, Slide, SlideAnalysis, SlideTiming, User
from app.services.presentations import get_owned_presentation_project

TIMING_STATUS_COMPLETED = "COMPLETED"
TIMING_NOT_FOUND_MESSAGE = "발표 시간 배분 결과를 찾을 수 없습니다."
TIMING_NOT_READY_MESSAGE = "시간을 배분할 슬라이드가 준비되지 않았습니다."
TIMING_TOTAL_MISMATCH_MESSAGE = "슬라이드별 배정 시간 합계가 발표 가능 시간과 일치하지 않습니다."
DEFAULT_TRANSITION_SECONDS = 5
MIN_SLIDE_ALLOCATED_SECONDS = 10


@dataclass(frozen=True)
class PresentationTimingResult:
    """Active timing allocation for one owned presentation."""

    presentation: Presentation
    timings: tuple[SlideTiming, ...]
    total_allocated_seconds: int


def _next_sqlite_slide_timing_id(db: Session) -> int | None:
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(SlideTiming.slide_timing_id), 0) + 1)).scalar_one()
    return int(next_id)


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


def _latest_slide_analysis_by_slide_id(db: Session, *, presentation_id: int) -> dict[int, SlideAnalysis]:
    latest_version = db.execute(
        select(func.max(SlideAnalysis.presentation_analysis_id))
        .join(Slide, Slide.slide_id == SlideAnalysis.slide_id)
        .where(Slide.presentation_id == presentation_id)
    ).scalar_one()
    if latest_version is None:
        return {}

    statement = select(SlideAnalysis).where(SlideAnalysis.presentation_analysis_id == latest_version)
    return {analysis.slide_id: analysis for analysis in db.execute(statement).scalars().all()}


def _latest_timing_version(db: Session, *, presentation_id: int) -> int:
    version = db.execute(
        select(func.coalesce(func.max(SlideTiming.version), 0))
        .join(Slide, Slide.slide_id == SlideTiming.slide_id)
        .where(Slide.presentation_id == presentation_id)
    ).scalar_one()
    return int(version)


def _active_timings(db: Session, *, presentation_id: int) -> list[SlideTiming]:
    statement = (
        select(SlideTiming)
        .join(Slide, Slide.slide_id == SlideTiming.slide_id)
        .options(selectinload(SlideTiming.slide))
        .where(
            Slide.presentation_id == presentation_id,
            Slide.excluded.is_(False),
            SlideTiming.is_active.is_(True),
        )
        .order_by(Slide.sort_order.asc(), Slide.slide_id.asc())
    )
    return list(db.execute(statement).scalars().all())


def _slide_weight(slide: Slide, analysis: SlideAnalysis | None) -> Decimal:
    if analysis is not None:
        importance = Decimal(analysis.importance_score or 1)
        complexity = Decimal(analysis.complexity_score or 1)
        return max(Decimal("1.0"), importance * Decimal("0.65") + complexity * Decimal("0.35"))

    text_length = len(" ".join(part or "" for part in (slide.title, slide.raw_text, slide.notes_text)))
    text_weight = min(Decimal(text_length) / Decimal("180"), Decimal("2.0"))
    position_weight = Decimal("0.5") if slide.sort_order == 1 else Decimal("0.0")
    return Decimal("1.0") + text_weight + position_weight


def _allocate_seconds(
    *,
    slides: list[Slide],
    analyses: dict[int, SlideAnalysis],
    total_seconds: int,
    locked_seconds_by_slide_id: dict[int, int] | None = None,
) -> dict[int, int]:
    locked_seconds_by_slide_id = locked_seconds_by_slide_id or {}
    locked_total = sum(locked_seconds_by_slide_id.values())
    if locked_total > total_seconds:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.TIMING_TOTAL_MISMATCH,
            message=TIMING_TOTAL_MISMATCH_MESSAGE,
            details={"availableSeconds": total_seconds, "lockedSeconds": locked_total},
        )

    allocations = dict(locked_seconds_by_slide_id)
    unlocked_slides = [slide for slide in slides if slide.slide_id not in locked_seconds_by_slide_id]
    if not unlocked_slides:
        if locked_total != total_seconds:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=ErrorCode.TIMING_TOTAL_MISMATCH,
                message=TIMING_TOTAL_MISMATCH_MESSAGE,
                details={"availableSeconds": total_seconds, "allocatedSeconds": locked_total},
            )
        return allocations

    remaining_seconds = total_seconds - locked_total
    minimum_required = len(unlocked_slides) * MIN_SLIDE_ALLOCATED_SECONDS
    if remaining_seconds < minimum_required:
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.TIMING_TOTAL_MISMATCH,
            message=TIMING_TOTAL_MISMATCH_MESSAGE,
            details={
                "availableSeconds": total_seconds,
                "lockedSeconds": locked_total,
                "minimumUnlockedSeconds": minimum_required,
            },
        )

    distributable_seconds = remaining_seconds - minimum_required
    weights = {slide.slide_id: _slide_weight(slide, analyses.get(slide.slide_id)) for slide in unlocked_slides}
    total_weight = sum(weights.values(), Decimal("0"))
    fractional: list[tuple[Decimal, int]] = []
    distributed = 0
    for slide in unlocked_slides:
        exact = Decimal(distributable_seconds) * weights[slide.slide_id] / total_weight if total_weight else Decimal("0")
        extra = int(exact)
        distributed += extra
        allocations[slide.slide_id] = MIN_SLIDE_ALLOCATED_SECONDS + extra
        fractional.append((exact - extra, slide.slide_id))

    for _fraction, slide_id in sorted(fractional, reverse=True)[: distributable_seconds - distributed]:
        allocations[slide_id] += 1
    return allocations


def _deactivate_existing_timings(db: Session, *, presentation_id: int) -> None:
    for timing in _active_timings(db, presentation_id=presentation_id):
        timing.is_active = False


def _create_timing_version(
    db: Session,
    *,
    presentation: Presentation,
    slides: list[Slide],
    allocations: dict[int, int],
    locked_slide_ids: set[int] | None = None,
    reason_prefix: str,
) -> PresentationTimingResult:
    locked_slide_ids = locked_slide_ids or set()
    _deactivate_existing_timings(db, presentation_id=presentation.presentation_id)
    version = _latest_timing_version(db, presentation_id=presentation.presentation_id) + 1
    next_timing_id = _next_sqlite_slide_timing_id(db)
    timings: list[SlideTiming] = []
    for index, slide in enumerate(slides):
        timing_kwargs: dict[str, object] = {
            "slide_id": slide.slide_id,
            "version": version,
            "allocated_seconds": allocations[slide.slide_id],
            "transition_seconds": 0 if index == len(slides) - 1 else DEFAULT_TRANSITION_SECONDS,
            "allocation_reason": f"{reason_prefix}: 중요도, 복잡도, 제외 상태를 반영했습니다.",
            "is_locked": slide.slide_id in locked_slide_ids,
            "is_active": True,
        }
        if next_timing_id is not None:
            timing_kwargs["slide_timing_id"] = next_timing_id
            next_timing_id += 1
        timing = SlideTiming(**timing_kwargs)
        db.add(timing)
        timings.append(timing)

    presentation.timing_status = TIMING_STATUS_COMPLETED
    db.commit()
    return get_latest_presentation_timings(db, user_id=presentation.user_id, presentation_id=presentation.presentation_id)


def generate_presentation_timings(db: Session, *, user: User, presentation_id: int) -> PresentationTimingResult:
    """Generate active slide timings for non-excluded slides."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    slides = _active_slides(db, presentation_id=presentation.presentation_id)
    if not slides:
        raise ApiError(
            status_code=HTTPStatus.CONFLICT,
            code=ErrorCode.TIMING_NOT_FOUND,
            message=TIMING_NOT_READY_MESSAGE,
            details={"presentationId": presentation.presentation_id},
        )

    allocations = _allocate_seconds(
        slides=slides,
        analyses=_latest_slide_analysis_by_slide_id(db, presentation_id=presentation.presentation_id),
        total_seconds=presentation.presentation_duration_seconds,
    )
    return _create_timing_version(
        db,
        presentation=presentation,
        slides=slides,
        allocations=allocations,
        reason_prefix="자동 배분",
    )


def get_latest_presentation_timings(
    db: Session,
    *,
    user: User | None = None,
    user_id: int | None = None,
    presentation_id: int,
) -> PresentationTimingResult:
    """Return active timings for one owned presentation."""

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
    timings = _active_timings(db, presentation_id=presentation.presentation_id)
    if not timings:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.TIMING_NOT_FOUND,
            message=TIMING_NOT_FOUND_MESSAGE,
        )
    total_allocated = sum(timing.allocated_seconds for timing in timings)
    if total_allocated != presentation.presentation_duration_seconds:
        raise ApiError(
            status_code=HTTPStatus.CONFLICT,
            code=ErrorCode.TIMING_TOTAL_MISMATCH,
            message=TIMING_TOTAL_MISMATCH_MESSAGE,
            details={
                "availableSeconds": presentation.presentation_duration_seconds,
                "allocatedSeconds": total_allocated,
            },
        )
    return PresentationTimingResult(
        presentation=presentation,
        timings=tuple(timings),
        total_allocated_seconds=total_allocated,
    )


def rebalance_presentation_timings(db: Session, *, user: User, presentation_id: int) -> PresentationTimingResult:
    """Rebalance unlocked timings while preserving manually locked slide durations."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    current_timings = _active_timings(db, presentation_id=presentation.presentation_id)
    if not current_timings:
        return generate_presentation_timings(db, user=user, presentation_id=presentation.presentation_id)

    slides = _active_slides(db, presentation_id=presentation.presentation_id)
    locked_seconds = {
        timing.slide_id: timing.allocated_seconds
        for timing in current_timings
        if timing.is_locked and not timing.slide.excluded
    }
    allocations = _allocate_seconds(
        slides=slides,
        analyses=_latest_slide_analysis_by_slide_id(db, presentation_id=presentation.presentation_id),
        total_seconds=presentation.presentation_duration_seconds,
        locked_seconds_by_slide_id=locked_seconds,
    )
    return _create_timing_version(
        db,
        presentation=presentation,
        slides=slides,
        allocations=allocations,
        locked_slide_ids=set(locked_seconds),
        reason_prefix="재분배",
    )


def update_slide_timing(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    slide_id: int,
    allocated_seconds: int,
) -> PresentationTimingResult:
    """Lock one slide duration and rebalance the remaining active slides."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    slides = _active_slides(db, presentation_id=presentation.presentation_id)
    if slide_id not in {slide.slide_id for slide in slides}:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.SLIDE_NOT_FOUND,
            message="슬라이드를 찾을 수 없습니다.",
        )

    current_locked = {
        timing.slide_id: timing.allocated_seconds
        for timing in _active_timings(db, presentation_id=presentation.presentation_id)
        if timing.is_locked and not timing.slide.excluded
    }
    current_locked[slide_id] = allocated_seconds
    allocations = _allocate_seconds(
        slides=slides,
        analyses=_latest_slide_analysis_by_slide_id(db, presentation_id=presentation.presentation_id),
        total_seconds=presentation.presentation_duration_seconds,
        locked_seconds_by_slide_id=current_locked,
    )
    return _create_timing_version(
        db,
        presentation=presentation,
        slides=slides,
        allocations=allocations,
        locked_slide_ids=set(current_locked),
        reason_prefix="수동 수정 후 재분배",
    )


__all__ = [
    "DEFAULT_TRANSITION_SECONDS",
    "MIN_SLIDE_ALLOCATED_SECONDS",
    "PresentationTimingResult",
    "TIMING_NOT_FOUND_MESSAGE",
    "TIMING_NOT_READY_MESSAGE",
    "TIMING_STATUS_COMPLETED",
    "TIMING_TOTAL_MISMATCH_MESSAGE",
    "generate_presentation_timings",
    "get_latest_presentation_timings",
    "rebalance_presentation_timings",
    "update_slide_timing",
]
