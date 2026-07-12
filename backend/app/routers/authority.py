import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_database_session
from app.models.user import User
from app.routers.dependencies import get_current_authority
from app.schemas.authority import (
    AuthorityAssessmentDetail,
    AuthorityDashboardResponse,
    ShortlistRequest,
    ShortlistResponse,
)
from app.services.biomechanical_visualization import VisualizationError
from app.services.authority import AuthorityAssessmentNotFoundError, AuthorityService
from app.services.report import AssessmentReportService, ReportNotFoundError
from app.services.video_processing import (
    AnnotatedVideoUnavailableError,
    UploadedVideoMissingError,
)


router = APIRouter(prefix="/api/v1/authority", tags=["authority"])


@router.get("/dashboard", response_model=AuthorityDashboardResponse)
async def authority_dashboard(
    current_authority: Annotated[User, Depends(get_current_authority)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    sport: str | None = None,
    state: str | None = None,
    min_age: Annotated[int | None, Query(ge=5, le=100)] = None,
    max_age: Annotated[int | None, Query(ge=5, le=100)] = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    max_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    shortlisted: bool | None = None,
) -> AuthorityDashboardResponse:
    return await AuthorityService(session).dashboard(
        sport=sport,
        state=state,
        min_age=min_age,
        max_age=max_age,
        min_score=min_score,
        max_score=max_score,
        shortlisted=shortlisted,
    )


@router.get("/assessments/{assessment_id}", response_model=AuthorityAssessmentDetail)
async def authority_assessment(
    assessment_id: uuid.UUID,
    current_authority: Annotated[User, Depends(get_current_authority)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuthorityAssessmentDetail:
    try:
        return await AuthorityService(session).assessment(assessment_id)
    except AuthorityAssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Assessment not found") from exc


@router.get("/assessments/{assessment_id}/report")
async def authority_assessment_report(
    assessment_id: uuid.UUID,
    current_authority: Annotated[User, Depends(get_current_authority)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Response:
    try:
        content, filename = await AssessmentReportService(session).for_authority(
            assessment_id=assessment_id
        )
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Assessment report not found") from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/assessments/{assessment_id}/video", response_class=FileResponse)
async def authority_video(
    assessment_id: uuid.UUID,
    current_authority: Annotated[User, Depends(get_current_authority)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FileResponse:
    try:
        path, content_type = await AuthorityService(session).video(assessment_id)
    except AuthorityAssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Assessment not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Video unavailable")
    return FileResponse(path, media_type=content_type)


@router.get(
    "/assessments/{assessment_id}/annotated-video", response_class=FileResponse
)
async def authority_annotated_video(
    assessment_id: uuid.UUID,
    current_authority: Annotated[User, Depends(get_current_authority)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FileResponse:
    try:
        path = await AuthorityService(session).annotated_video(assessment_id)
    except AuthorityAssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Assessment not found") from exc
    except UploadedVideoMissingError as exc:
        raise HTTPException(status_code=410, detail="Video unavailable") from exc
    except (AnnotatedVideoUnavailableError, VisualizationError) as exc:
        raise HTTPException(
            status_code=404, detail="Annotated video unavailable"
        ) from exc
    return FileResponse(path, media_type="video/mp4")


@router.post(
    "/assessments/{assessment_id}/shortlist", response_model=ShortlistResponse
)
async def shortlist_athlete(
    assessment_id: uuid.UUID,
    payload: ShortlistRequest,
    current_authority: Annotated[User, Depends(get_current_authority)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ShortlistResponse:
    try:
        return await AuthorityService(session).shortlist(
            assessment_id=assessment_id,
            authority_id=current_authority.id,
            remarks=payload.remarks,
        )
    except AuthorityAssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Assessment not found") from exc
