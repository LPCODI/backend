"""Presentation project API routes."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db import get_db
from app.schemas import PresentationCreateRequest, PresentationResponse, PresentationTag, SuccessResponse
from app.services import create_presentation_project, get_presentation_project, list_presentation_projects

router = APIRouter(prefix="/presentations", tags=[PresentationTag.PRESENTATIONS])


@router.get("", response_model=SuccessResponse[list[PresentationResponse]])
def list_presentations(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[list[PresentationResponse]]:
    """List presentation projects owned by the authenticated user."""

    presentations = list_presentation_projects(db, user=current_user)
    return SuccessResponse(
        data=[PresentationResponse.model_validate(presentation) for presentation in presentations],
    )


@router.get("/{presentationId}", response_model=SuccessResponse[PresentationResponse])
def get_presentation(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationResponse]:
    """Return one presentation project owned by the authenticated user."""

    presentation = get_presentation_project(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=PresentationResponse.model_validate(presentation))


@router.post(
    "",
    response_model=SuccessResponse[PresentationResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_presentation(
    request: PresentationCreateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationResponse]:
    """Create a professor-facing university project presentation."""

    presentation = create_presentation_project(
        db,
        user=current_user,
        title=request.title,
        total_duration_seconds=request.total_duration_seconds,
        qa_duration_seconds=request.qa_duration_seconds,
    )
    return SuccessResponse(
        data=PresentationResponse.model_validate(presentation),
        message=HTTPStatus.CREATED.phrase,
    )
