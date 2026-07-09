"""Presentation project domain services."""

from dataclasses import dataclass
from http import HTTPStatus

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import ApiError
from app.domain import ErrorCode, PresentationStatus
from app.models import Presentation, User

MIN_TOTAL_DURATION_SECONDS = 120
MAX_TOTAL_DURATION_SECONDS = 7_200
MIN_PRESENTATION_DURATION_SECONDS = 60
PRESENTATION_INVALID_TIME_RANGE_MESSAGE = "발표 시간 조건이 올바르지 않습니다."
PRESENTATION_INVALID_STATUS_TRANSITION_MESSAGE = "발표 프로젝트 상태 전이가 올바르지 않습니다."
PRESENTATION_NOT_FOUND_MESSAGE = "발표 프로젝트를 찾을 수 없습니다."
PRESENTATION_DUPLICATE_TITLE_SUFFIX = " (복사본)"
PRESENTATION_STATUS_TRANSITIONS: dict[PresentationStatus, frozenset[PresentationStatus]] = {
    PresentationStatus.DRAFT: frozenset(
        {
            PresentationStatus.FILE_UPLOADED,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.FILE_UPLOADED: frozenset(
        {
            PresentationStatus.PARSING,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.PARSING: frozenset(
        {
            PresentationStatus.PARSED,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.PARSED: frozenset(
        {
            PresentationStatus.ANALYZING,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.ANALYZING: frozenset(
        {
            PresentationStatus.ANALYZED,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.ANALYZED: frozenset(
        {
            PresentationStatus.ANALYZING,
            PresentationStatus.SCRIPT_GENERATING,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.SCRIPT_GENERATING: frozenset(
        {
            PresentationStatus.SCRIPT_READY,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.SCRIPT_READY: frozenset(
        {
            PresentationStatus.REHEARSAL_READY,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.REHEARSAL_READY: frozenset(
        {
            PresentationStatus.COMPLETED,
            PresentationStatus.FAILED,
        }
    ),
    PresentationStatus.COMPLETED: frozenset(),
    PresentationStatus.FAILED: frozenset(),
}


@dataclass(frozen=True)
class PresentationTimeValidationResult:
    """Validated presentation time inputs and derived speaking duration."""

    total_duration_seconds: int
    qa_duration_seconds: int
    presentation_duration_seconds: int


def _invalid_time_range_error(reason: str) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.BAD_REQUEST,
        code=ErrorCode.PRESENTATION_INVALID_TIME_RANGE,
        message=PRESENTATION_INVALID_TIME_RANGE_MESSAGE,
        details={
            "reason": reason,
            "minTotalDurationSeconds": MIN_TOTAL_DURATION_SECONDS,
            "maxTotalDurationSeconds": MAX_TOTAL_DURATION_SECONDS,
            "minPresentationDurationSeconds": MIN_PRESENTATION_DURATION_SECONDS,
        },
    )


def _normalize_presentation_status(status: PresentationStatus | str) -> PresentationStatus:
    return status if isinstance(status, PresentationStatus) else PresentationStatus(status)


def get_allowed_presentation_status_transitions(
    current_status: PresentationStatus | str,
) -> frozenset[PresentationStatus]:
    """Return valid next states for the current presentation status."""

    normalized_status = _normalize_presentation_status(current_status)
    return PRESENTATION_STATUS_TRANSITIONS[normalized_status]


def validate_presentation_status_transition(
    *,
    current_status: PresentationStatus | str,
    next_status: PresentationStatus | str,
) -> None:
    """Validate presentation project state changes against the documented workflow."""

    normalized_current_status = _normalize_presentation_status(current_status)
    normalized_next_status = _normalize_presentation_status(next_status)
    if normalized_current_status == normalized_next_status:
        return

    allowed_statuses = get_allowed_presentation_status_transitions(normalized_current_status)
    if normalized_next_status in allowed_statuses:
        return

    raise ApiError(
        status_code=HTTPStatus.CONFLICT,
        code=ErrorCode.PRESENTATION_INVALID_STATUS_TRANSITION,
        message=PRESENTATION_INVALID_STATUS_TRANSITION_MESSAGE,
        details={
            "currentStatus": normalized_current_status.value,
            "nextStatus": normalized_next_status.value,
            "allowedNextStatuses": sorted(status.value for status in allowed_statuses),
        },
    )


def validate_presentation_time_input(
    *,
    total_duration_seconds: int,
    qa_duration_seconds: int,
) -> PresentationTimeValidationResult:
    """Validate project time inputs from the API specification."""

    if total_duration_seconds < MIN_TOTAL_DURATION_SECONDS:
        raise _invalid_time_range_error("total_duration_too_short")
    if total_duration_seconds > MAX_TOTAL_DURATION_SECONDS:
        raise _invalid_time_range_error("total_duration_too_long")
    if qa_duration_seconds < 0:
        raise _invalid_time_range_error("qa_duration_negative")
    if qa_duration_seconds >= total_duration_seconds:
        raise _invalid_time_range_error("qa_duration_not_less_than_total")

    presentation_duration_seconds = total_duration_seconds - qa_duration_seconds
    if presentation_duration_seconds < MIN_PRESENTATION_DURATION_SECONDS:
        raise _invalid_time_range_error("presentation_duration_too_short")

    return PresentationTimeValidationResult(
        total_duration_seconds=total_duration_seconds,
        qa_duration_seconds=qa_duration_seconds,
        presentation_duration_seconds=presentation_duration_seconds,
    )


def calculate_presentation_duration_seconds(
    *,
    total_duration_seconds: int,
    qa_duration_seconds: int,
) -> int:
    """Calculate available speaking time after reserving Q&A time."""

    return validate_presentation_time_input(
        total_duration_seconds=total_duration_seconds,
        qa_duration_seconds=qa_duration_seconds,
    ).presentation_duration_seconds


def _next_sqlite_presentation_id(db: Session) -> int | None:
    """Return a presentation id for SQLite, whose BIGINT identity columns do not autoincrement."""

    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        return None
    next_id = db.execute(select(func.coalesce(func.max(Presentation.presentation_id), 0) + 1)).scalar_one()
    return int(next_id)


def create_presentation_project(
    db: Session,
    *,
    user: User,
    title: str,
    total_duration_seconds: int,
    qa_duration_seconds: int,
) -> Presentation:
    """Create a presentation project for the authenticated user."""

    time_result = validate_presentation_time_input(
        total_duration_seconds=total_duration_seconds,
        qa_duration_seconds=qa_duration_seconds,
    )
    presentation_kwargs: dict[str, object] = {
        "user_id": user.user_id,
        "title": title.strip(),
        "total_duration_seconds": time_result.total_duration_seconds,
        "qa_duration_seconds": time_result.qa_duration_seconds,
        "presentation_duration_seconds": time_result.presentation_duration_seconds,
    }
    sqlite_presentation_id = _next_sqlite_presentation_id(db)
    if sqlite_presentation_id is not None:
        presentation_kwargs["presentation_id"] = sqlite_presentation_id

    presentation = Presentation(**presentation_kwargs)
    db.add(presentation)
    db.commit()
    db.refresh(presentation)
    return presentation


def list_presentation_projects(db: Session, *, user: User) -> list[Presentation]:
    """Return non-deleted presentation projects owned by the authenticated user."""

    statement = (
        select(Presentation)
        .where(
            Presentation.user_id == user.user_id,
            Presentation.deleted_at.is_(None),
        )
        .order_by(Presentation.created_at.desc(), Presentation.presentation_id.desc())
    )
    return list(db.execute(statement).scalars().all())


def get_owned_presentation_project(db: Session, *, user: User, presentation_id: int) -> Presentation:
    """Return one non-deleted presentation project after ownership verification."""

    statement = select(Presentation).where(
        Presentation.presentation_id == presentation_id,
        Presentation.user_id == user.user_id,
        Presentation.deleted_at.is_(None),
    )
    presentation = db.execute(statement).scalar_one_or_none()
    if presentation is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.PRESENTATION_NOT_FOUND,
            message=PRESENTATION_NOT_FOUND_MESSAGE,
        )
    return presentation


def get_presentation_project(db: Session, *, user: User, presentation_id: int) -> Presentation:
    """Return one non-deleted presentation project owned by the authenticated user."""

    return get_owned_presentation_project(db, user=user, presentation_id=presentation_id)


def update_presentation_project(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    updates: dict[str, object],
) -> Presentation:
    """Update editable presentation project fields for the authenticated owner."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)

    next_total_duration_seconds = int(
        updates.get("total_duration_seconds", presentation.total_duration_seconds),
    )
    next_qa_duration_seconds = int(
        updates.get("qa_duration_seconds", presentation.qa_duration_seconds),
    )
    time_result = validate_presentation_time_input(
        total_duration_seconds=next_total_duration_seconds,
        qa_duration_seconds=next_qa_duration_seconds,
    )

    if "title" in updates:
        presentation.title = str(updates["title"]).strip()
    presentation.total_duration_seconds = time_result.total_duration_seconds
    presentation.qa_duration_seconds = time_result.qa_duration_seconds
    presentation.presentation_duration_seconds = time_result.presentation_duration_seconds

    db.commit()
    db.refresh(presentation)
    return presentation


def delete_presentation_project(db: Session, *, user: User, presentation_id: int) -> None:
    """Soft-delete one presentation project owned by the authenticated user."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    presentation.soft_delete()
    db.commit()


def duplicate_presentation_project(db: Session, *, user: User, presentation_id: int) -> Presentation:
    """Duplicate one presentation project owned by the authenticated user."""

    source = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    presentation_kwargs: dict[str, object] = {
        "user_id": user.user_id,
        "title": f"{source.title}{PRESENTATION_DUPLICATE_TITLE_SUFFIX}",
        "total_duration_seconds": source.total_duration_seconds,
        "qa_duration_seconds": source.qa_duration_seconds,
        "presentation_duration_seconds": source.presentation_duration_seconds,
        "presentation_context": source.presentation_context,
        "status": PresentationStatus.DRAFT,
        "timing_status": source.timing_status,
        "script_status": source.script_status,
        "duplicated_from_id": source.presentation_id,
    }
    sqlite_presentation_id = _next_sqlite_presentation_id(db)
    if sqlite_presentation_id is not None:
        presentation_kwargs["presentation_id"] = sqlite_presentation_id

    duplicate = Presentation(**presentation_kwargs)
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return duplicate


def transition_presentation_project_status(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    next_status: PresentationStatus,
) -> Presentation:
    """Persist a valid presentation project state transition for the authenticated owner."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    validate_presentation_status_transition(
        current_status=presentation.status,
        next_status=next_status,
    )
    presentation.status = next_status
    db.commit()
    db.refresh(presentation)
    return presentation


__all__ = [
    "MAX_TOTAL_DURATION_SECONDS",
    "MIN_PRESENTATION_DURATION_SECONDS",
    "MIN_TOTAL_DURATION_SECONDS",
    "PRESENTATION_DUPLICATE_TITLE_SUFFIX",
    "PRESENTATION_INVALID_STATUS_TRANSITION_MESSAGE",
    "PRESENTATION_INVALID_TIME_RANGE_MESSAGE",
    "PRESENTATION_NOT_FOUND_MESSAGE",
    "PRESENTATION_STATUS_TRANSITIONS",
    "PresentationTimeValidationResult",
    "calculate_presentation_duration_seconds",
    "create_presentation_project",
    "delete_presentation_project",
    "duplicate_presentation_project",
    "get_allowed_presentation_status_transitions",
    "get_owned_presentation_project",
    "get_presentation_project",
    "list_presentation_projects",
    "transition_presentation_project_status",
    "update_presentation_project",
    "validate_presentation_status_transition",
    "validate_presentation_time_input",
]
