"""Presentation project API routes."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_request_settings
from app.core import Settings
from app.db import get_db
from app.schemas import (
    PresentationFileResponse,
    PresentationCreateRequest,
    PresentationResponse,
    PresentationTag,
    PresentationUpdateRequest,
    SuccessResponse,
)
from app.services import (
    create_presentation_project,
    create_presentation_file,
    delete_presentation_file,
    delete_presentation_project,
    duplicate_presentation_project,
    get_presentation_project,
    list_presentation_files,
    list_presentation_projects,
    update_presentation_project,
)

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


@router.delete("/{presentationId}", response_model=SuccessResponse[None])
def delete_presentation(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[None]:
    """Soft-delete one presentation project owned by the authenticated user."""

    delete_presentation_project(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=None)


@router.post(
    "/{presentationId}/duplicate",
    response_model=SuccessResponse[PresentationResponse],
    status_code=status.HTTP_201_CREATED,
)
def duplicate_presentation(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationResponse]:
    """Duplicate one presentation project owned by the authenticated user."""

    presentation = duplicate_presentation_project(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(
        data=PresentationResponse.model_validate(presentation),
        message=HTTPStatus.CREATED.phrase,
    )


@router.patch("/{presentationId}", response_model=SuccessResponse[PresentationResponse])
def update_presentation(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    request: PresentationUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationResponse]:
    """Update editable presentation fields while preserving fixed professor-project conditions."""

    presentation = update_presentation_project(
        db,
        user=current_user,
        presentation_id=presentation_id,
        updates=request.model_dump(exclude_unset=True),
    )
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


@router.post(
    "/{presentationId}/files",
    response_model=SuccessResponse[PresentationFileResponse],
    status_code=status.HTTP_201_CREATED,
    tags=[PresentationTag.PRESENTATION_FILES],
)
async def upload_presentation_file(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    file: UploadFile = File(...),
) -> SuccessResponse[PresentationFileResponse]:
    """Upload and store one presentation material file for an owned project."""

    content = await file.read()
    presentation_file = create_presentation_file(
        db,
        user=current_user,
        presentation_id=presentation_id,
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
        settings=settings,
    )
    return SuccessResponse(
        data=PresentationFileResponse.model_validate(presentation_file),
        message=HTTPStatus.CREATED.phrase,
    )


@router.get(
    "/{presentationId}/files",
    response_model=SuccessResponse[list[PresentationFileResponse]],
    tags=[PresentationTag.PRESENTATION_FILES],
)
def list_files(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[list[PresentationFileResponse]]:
    """List uploaded material files for an owned presentation project."""

    files = list_presentation_files(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=[PresentationFileResponse.model_validate(file) for file in files])


@router.delete(
    "/{presentationId}/files/{fileId}",
    response_model=SuccessResponse[None],
    tags=[PresentationTag.PRESENTATION_FILES],
)
def delete_file(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    file_id: Annotated[int, Path(alias="fileId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> SuccessResponse[None]:
    """Soft-delete one uploaded material file for an owned presentation project."""

    delete_presentation_file(
        db,
        user=current_user,
        presentation_id=presentation_id,
        file_id=file_id,
        settings=settings,
    )
    return SuccessResponse(data=None)
