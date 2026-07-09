"""Presentation project API routes."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Path, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_request_settings
from app.core import Settings
from app.db import get_db
from app.schemas import (
    ParsedSlideResponse,
    PresentationAnalysisResponse,
    PresentationFileResponse,
    PresentationCreateRequest,
    PresentationParseRequest,
    PresentationParseResultResponse,
    PresentationParseResponse,
    PresentationResponse,
    PresentationScriptResponse,
    PresentationTag,
    PresentationTimingResponse,
    PresentationUpdateRequest,
    SlideOrderUpdateRequest,
    SlideAnalysisResponse,
    SlideResponse,
    SlideScriptResponse,
    SlideTimingResponse,
    SlideTimingUpdateRequest,
    SlideUpdateRequest,
    SuccessResponse,
)
from app.services import (
    analyze_presentation_material,
    create_presentation_project,
    create_presentation_file,
    delete_presentation_file,
    delete_presentation_project,
    duplicate_presentation_project,
    get_presentation_project,
    get_presentation_parse_result,
    generate_presentation_timings,
    get_latest_presentation_analysis,
    get_latest_presentation_timings,
    get_latest_slide_analysis,
    get_owned_slide,
    list_presentation_slides,
    list_presentation_files,
    list_presentation_projects,
    parse_presentation_file,
    persist_presentation_script_drafts,
    rebalance_presentation_timings,
    reorder_presentation_slides,
    set_slide_excluded,
    update_presentation_project,
    update_presentation_slide,
    update_slide_timing,
)

router = APIRouter(prefix="/presentations", tags=[PresentationTag.PRESENTATIONS])


def _analysis_response(analysis_result) -> PresentationAnalysisResponse:
    analysis = analysis_result.analysis
    return PresentationAnalysisResponse(
        presentation_analysis_id=analysis.presentation_analysis_id,
        presentation_id=analysis.presentation_id,
        version=analysis.version,
        summary=analysis.summary,
        overall_core_message=analysis.overall_core_message,
        strengths=analysis.strengths,
        weaknesses=analysis.weaknesses,
        professor_question_points=analysis.professor_question_points,
        model_name=analysis.model_name,
        prompt_version=analysis.prompt_version,
        status=analysis.status,
        created_at=analysis.created_at,
        slide_analyses=[
            SlideAnalysisResponse.model_validate(slide_analysis)
            for slide_analysis in analysis_result.slide_analyses
        ],
    )


def _timing_response(timing_result) -> PresentationTimingResponse:
    presentation = timing_result.presentation
    return PresentationTimingResponse(
        presentation_id=presentation.presentation_id,
        presentation_duration_seconds=presentation.presentation_duration_seconds,
        total_allocated_seconds=timing_result.total_allocated_seconds,
        status=presentation.timing_status,
        timings=[SlideTimingResponse.model_validate(timing) for timing in timing_result.timings],
    )


def _script_response(script_result) -> PresentationScriptResponse:
    presentation = script_result.presentation
    return PresentationScriptResponse(
        presentation_id=presentation.presentation_id,
        status=presentation.script_status,
        scripts=[SlideScriptResponse.model_validate(script) for script in script_result.scripts],
    )


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


@router.post(
    "/{presentationId}/parse",
    response_model=SuccessResponse[PresentationParseResponse],
    status_code=status.HTTP_202_ACCEPTED,
    tags=[PresentationTag.PRESENTATION_FILES],
)
async def parse_presentation_material(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    request: PresentationParseRequest = Body(default_factory=PresentationParseRequest),
) -> SuccessResponse[PresentationParseResponse]:
    """Parse an uploaded material file and persist slide rows for an owned project."""

    parse_summary = await parse_presentation_file(
        db,
        user=current_user,
        presentation_id=presentation_id,
        settings=settings,
        file_id=request.file_id,
    )
    return SuccessResponse(
        data=PresentationParseResponse(
            presentation_id=parse_summary.presentation_id,
            file_id=parse_summary.file_id,
            status=parse_summary.status,
            slide_count=parse_summary.slide_count,
            parser_provider=parse_summary.parser_provider,
            parser_version=parse_summary.parser_version,
            warnings=list(parse_summary.warnings),
        ),
        message=HTTPStatus.ACCEPTED.phrase,
    )


@router.get(
    "/{presentationId}/parse-result",
    response_model=SuccessResponse[PresentationParseResultResponse],
    tags=[PresentationTag.PRESENTATION_FILES],
)
def get_presentation_parse_result_route(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationParseResultResponse]:
    """Return latest material parse state and persisted slides for an owned project."""

    parse_result = get_presentation_parse_result(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(
        data=PresentationParseResultResponse(
            presentation_id=presentation_id,
            file=PresentationFileResponse.model_validate(parse_result.presentation_file),
            slide_count=len(parse_result.slides),
            slides=[ParsedSlideResponse.model_validate(slide) for slide in parse_result.slides],
        )
    )


@router.post(
    "/{presentationId}/analysis",
    response_model=SuccessResponse[PresentationAnalysisResponse],
    status_code=status.HTTP_202_ACCEPTED,
    tags=[PresentationTag.ANALYSIS],
)
def analyze_presentation(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationAnalysisResponse]:
    """Analyze parsed presentation material and persist a versioned result."""

    analysis_result = analyze_presentation_material(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(
        data=_analysis_response(analysis_result),
        message=HTTPStatus.ACCEPTED.phrase,
    )


@router.get(
    "/{presentationId}/analysis",
    response_model=SuccessResponse[PresentationAnalysisResponse],
    tags=[PresentationTag.ANALYSIS],
)
def get_presentation_analysis(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationAnalysisResponse]:
    """Return the latest whole-presentation analysis for an owned project."""

    analysis_result = get_latest_presentation_analysis(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=_analysis_response(analysis_result))


@router.get(
    "/{presentationId}/slides/{slideId}/analysis",
    response_model=SuccessResponse[SlideAnalysisResponse],
    tags=[PresentationTag.ANALYSIS],
)
def get_slide_analysis(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    slide_id: Annotated[int, Path(alias="slideId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[SlideAnalysisResponse]:
    """Return the latest slide analysis for one owned project slide."""

    slide_analysis = get_latest_slide_analysis(
        db,
        user=current_user,
        presentation_id=presentation_id,
        slide_id=slide_id,
    )
    return SuccessResponse(data=SlideAnalysisResponse.model_validate(slide_analysis))


@router.post(
    "/{presentationId}/analysis/regenerate",
    response_model=SuccessResponse[PresentationAnalysisResponse],
    status_code=status.HTTP_202_ACCEPTED,
    tags=[PresentationTag.ANALYSIS],
)
def regenerate_presentation_analysis(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationAnalysisResponse]:
    """Generate a new analysis version for the latest parsed slide state."""

    analysis_result = analyze_presentation_material(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(
        data=_analysis_response(analysis_result),
        message=HTTPStatus.ACCEPTED.phrase,
    )


@router.post(
    "/{presentationId}/timings/generate",
    response_model=SuccessResponse[PresentationTimingResponse],
    status_code=status.HTTP_202_ACCEPTED,
    tags=[PresentationTag.TIMINGS],
)
def generate_timings(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationTimingResponse]:
    """Generate slide time allocation for non-excluded slides."""

    timing_result = generate_presentation_timings(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=_timing_response(timing_result), message=HTTPStatus.ACCEPTED.phrase)


@router.get(
    "/{presentationId}/timings",
    response_model=SuccessResponse[PresentationTimingResponse],
    tags=[PresentationTag.TIMINGS],
)
def get_timings(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationTimingResponse]:
    """Return the latest active timing allocation for an owned project."""

    timing_result = get_latest_presentation_timings(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=_timing_response(timing_result))


@router.patch(
    "/{presentationId}/timings/{slideId}",
    response_model=SuccessResponse[PresentationTimingResponse],
    tags=[PresentationTag.TIMINGS],
)
def update_timing(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    slide_id: Annotated[int, Path(alias="slideId", ge=1)],
    request: SlideTimingUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationTimingResponse]:
    """Lock one slide duration and rebalance the remaining slides."""

    timing_result = update_slide_timing(
        db,
        user=current_user,
        presentation_id=presentation_id,
        slide_id=slide_id,
        allocated_seconds=request.allocated_seconds,
    )
    return SuccessResponse(data=_timing_response(timing_result))


@router.post(
    "/{presentationId}/timings/rebalance",
    response_model=SuccessResponse[PresentationTimingResponse],
    status_code=status.HTTP_202_ACCEPTED,
    tags=[PresentationTag.TIMINGS],
)
def rebalance_timings(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationTimingResponse]:
    """Rebalance timing allocation while preserving locked slide durations."""

    timing_result = rebalance_presentation_timings(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=_timing_response(timing_result), message=HTTPStatus.ACCEPTED.phrase)


@router.post(
    "/{presentationId}/scripts/generate",
    response_model=SuccessResponse[PresentationScriptResponse],
    status_code=status.HTTP_202_ACCEPTED,
    tags=[PresentationTag.SCRIPTS],
)
def generate_scripts(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[PresentationScriptResponse]:
    """Generate and persist professor-facing scripts for non-excluded slides."""

    script_result = persist_presentation_script_drafts(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=_script_response(script_result), message=HTTPStatus.ACCEPTED.phrase)


@router.get(
    "/{presentationId}/slides",
    response_model=SuccessResponse[list[SlideResponse]],
    tags=[PresentationTag.SLIDES],
)
def list_slides(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[list[SlideResponse]]:
    """List parsed slides for an owned presentation project."""

    slides = list_presentation_slides(db, user=current_user, presentation_id=presentation_id)
    return SuccessResponse(data=[SlideResponse.model_validate(slide) for slide in slides])


@router.patch(
    "/{presentationId}/slides/order",
    response_model=SuccessResponse[list[SlideResponse]],
    tags=[PresentationTag.SLIDES],
)
def update_slide_order(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    request: SlideOrderUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[list[SlideResponse]]:
    """Replace slide order for an owned presentation project."""

    slides = reorder_presentation_slides(
        db,
        user=current_user,
        presentation_id=presentation_id,
        slide_ids=request.slide_ids,
    )
    return SuccessResponse(data=[SlideResponse.model_validate(slide) for slide in slides])


@router.get(
    "/{presentationId}/slides/{slideId}",
    response_model=SuccessResponse[SlideResponse],
    tags=[PresentationTag.SLIDES],
)
def get_slide(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    slide_id: Annotated[int, Path(alias="slideId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[SlideResponse]:
    """Return one parsed slide for an owned presentation project."""

    slide = get_owned_slide(db, user=current_user, presentation_id=presentation_id, slide_id=slide_id)
    return SuccessResponse(data=SlideResponse.model_validate(slide))


@router.patch(
    "/{presentationId}/slides/{slideId}",
    response_model=SuccessResponse[SlideResponse],
    tags=[PresentationTag.SLIDES],
)
def update_slide(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    slide_id: Annotated[int, Path(alias="slideId", ge=1)],
    request: SlideUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[SlideResponse]:
    """Update editable parsed slide content."""

    slide = update_presentation_slide(
        db,
        user=current_user,
        presentation_id=presentation_id,
        slide_id=slide_id,
        updates=request.model_dump(exclude_unset=True),
    )
    return SuccessResponse(data=SlideResponse.model_validate(slide))


@router.post(
    "/{presentationId}/slides/{slideId}/exclude",
    response_model=SuccessResponse[SlideResponse],
    tags=[PresentationTag.SLIDES],
)
def exclude_slide(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    slide_id: Annotated[int, Path(alias="slideId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[SlideResponse]:
    """Exclude a slide from later analysis and script generation."""

    slide = set_slide_excluded(
        db,
        user=current_user,
        presentation_id=presentation_id,
        slide_id=slide_id,
        excluded=True,
    )
    return SuccessResponse(data=SlideResponse.model_validate(slide))


@router.delete(
    "/{presentationId}/slides/{slideId}/exclude",
    response_model=SuccessResponse[SlideResponse],
    tags=[PresentationTag.SLIDES],
)
def include_slide(
    presentation_id: Annotated[int, Path(alias="presentationId", ge=1)],
    slide_id: Annotated[int, Path(alias="slideId", ge=1)],
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SuccessResponse[SlideResponse]:
    """Clear slide exclusion from later analysis and script generation."""

    slide = set_slide_excluded(
        db,
        user=current_user,
        presentation_id=presentation_id,
        slide_id=slide_id,
        excluded=False,
    )
    return SuccessResponse(data=SlideResponse.model_validate(slide))
