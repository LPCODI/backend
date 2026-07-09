"""Slide query, editing, ordering, and exclusion services."""

from http import HTTPStatus

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ApiError
from app.domain import ErrorCode
from app.models import Slide, User
from app.services.presentations import get_owned_presentation_project

SLIDE_NOT_FOUND_MESSAGE = "슬라이드를 찾을 수 없습니다."
SLIDE_INVALID_ORDER_MESSAGE = "슬라이드 순서가 올바르지 않습니다."


def list_presentation_slides(db: Session, *, user: User, presentation_id: int) -> list[Slide]:
    """Return slides for one owned presentation ordered by current sort order."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = (
        select(Slide)
        .where(Slide.presentation_id == presentation.presentation_id)
        .order_by(Slide.sort_order.asc(), Slide.slide_id.asc())
    )
    return list(db.execute(statement).scalars().all())


def get_owned_slide(db: Session, *, user: User, presentation_id: int, slide_id: int) -> Slide:
    """Return one slide after presentation ownership verification."""

    presentation = get_owned_presentation_project(db, user=user, presentation_id=presentation_id)
    statement = select(Slide).where(
        Slide.slide_id == slide_id,
        Slide.presentation_id == presentation.presentation_id,
    )
    slide = db.execute(statement).scalar_one_or_none()
    if slide is None:
        raise ApiError(
            status_code=HTTPStatus.NOT_FOUND,
            code=ErrorCode.SLIDE_NOT_FOUND,
            message=SLIDE_NOT_FOUND_MESSAGE,
        )
    return slide


def update_presentation_slide(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    slide_id: int,
    updates: dict[str, object],
) -> Slide:
    """Update editable slide content fields."""

    slide = get_owned_slide(db, user=user, presentation_id=presentation_id, slide_id=slide_id)
    for field_name in ("title", "raw_text", "notes_text", "image_url", "image_object_key"):
        if field_name in updates:
            value = updates[field_name]
            setattr(slide, field_name, value if value is None else str(value).strip())
    db.commit()
    db.refresh(slide)
    return slide


def reorder_presentation_slides(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    slide_ids: list[int],
) -> list[Slide]:
    """Replace slide sort order with the exact provided slide id sequence."""

    slides = list_presentation_slides(db, user=user, presentation_id=presentation_id)
    existing_ids = [slide.slide_id for slide in slides]
    if len(slide_ids) != len(existing_ids) or set(slide_ids) != set(existing_ids):
        raise ApiError(
            status_code=HTTPStatus.BAD_REQUEST,
            code=ErrorCode.SLIDE_INVALID_ORDER,
            message=SLIDE_INVALID_ORDER_MESSAGE,
            details={
                "expectedSlideIds": existing_ids,
                "receivedSlideIds": slide_ids,
            },
        )

    slides_by_id = {slide.slide_id: slide for slide in slides}
    for index, slide in enumerate(slides, start=1):
        slide.sort_order = -index
    db.flush()

    for sort_order, slide_id in enumerate(slide_ids, start=1):
        slides_by_id[slide_id].sort_order = sort_order
    db.commit()
    return list_presentation_slides(db, user=user, presentation_id=presentation_id)


def set_slide_excluded(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    slide_id: int,
    excluded: bool,
) -> Slide:
    """Set whether a slide is excluded from later analysis and script generation."""

    slide = get_owned_slide(db, user=user, presentation_id=presentation_id, slide_id=slide_id)
    slide.excluded = excluded
    db.commit()
    db.refresh(slide)
    return slide


__all__ = [
    "SLIDE_INVALID_ORDER_MESSAGE",
    "SLIDE_NOT_FOUND_MESSAGE",
    "get_owned_slide",
    "list_presentation_slides",
    "reorder_presentation_slides",
    "set_slide_excluded",
    "update_presentation_slide",
]
