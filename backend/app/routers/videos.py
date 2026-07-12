import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_database_session
from app.models.user import User
from app.routers.dependencies import get_current_media_user, get_current_user
from app.schemas.benchmark import BenchmarkScores
from app.schemas.biomechanics import BiomechanicalMetrics, CoachReplayTimeline
from app.schemas.leaderboard import LeaderboardResponse
from app.schemas.processing import VideoProcessingResponse
from app.schemas.progress import AthleteProgressAnalytics
from app.schemas.recommendation import (
    AssessmentDetail,
    AssessmentHistoryItem,
    RecommendationResult,
)
from app.schemas.video import Sport, VideoUploadResponse
from app.services.assessment import (
    AssessmentNotReadyError,
    AssessmentService,
    AssessmentUploadNotFoundError,
)
from app.services.leaderboard import LeaderboardService
from app.services.mediapipe_pose import PoseExtractionError
from app.services.progress_analytics import ProgressAnalyticsService
from app.services.report import AssessmentReportService, ReportNotFoundError
from app.services.biomechanical_visualization import VisualizationError
from app.services.stored_analysis import (
    AnalysisUploadNotFoundError,
    NoPoseDetectedError,
    PoseProcessingRequiredError,
    StoredAnalysisService,
)
from app.services.video_processing import (
    AnnotatedVideoUnavailableError,
    UploadedVideoMissingError,
    UploadNotFoundError,
    VideoProcessingService,
)
from app.services.video_service import VideoUploadService
from app.services.video_storage import (
    EmptyVideoError,
    UnsupportedVideoTypeError,
    VideoTooLargeError,
)
from app.services.video_quality import VideoQualityError

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("/{upload_id}/biomechanics", response_model=BiomechanicalMetrics)
async def calculate_stored_biomechanics(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BiomechanicalMetrics:
    try:
        return await StoredAnalysisService(session).calculate_biomechanics(
            upload_id=upload_id, athlete_id=current_user.id
        )
    except AnalysisUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except PoseProcessingRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pose processing must be completed first",
        ) from exc
    except NoPoseDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/{upload_id}/benchmark", response_model=BenchmarkScores)
async def compare_stored_benchmark(
    upload_id: uuid.UUID,
    metrics: BiomechanicalMetrics,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BenchmarkScores:
    try:
        return await StoredAnalysisService(session).compare_benchmark(
            upload_id=upload_id,
            athlete_id=current_user.id,
            metrics=metrics,
        )
    except AnalysisUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc


@router.get("/history", response_model=list[AssessmentHistoryItem])
async def assessment_history(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[AssessmentHistoryItem]:
    return await AssessmentService(session).history(athlete_id=current_user.id)


@router.get("/analytics/progress", response_model=AthleteProgressAnalytics)
async def athlete_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AthleteProgressAnalytics:
    return await ProgressAnalyticsService(session).get(athlete_id=current_user.id)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def athlete_leaderboard(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    sport: str | None = None,
    state: str | None = None,
    gender: str | None = None,
    min_age: Annotated[int | None, Query(ge=5, le=100)] = None,
    max_age: Annotated[int | None, Query(ge=5, le=100)] = None,
    min_experience: Annotated[int | None, Query(ge=0, le=80)] = None,
    max_experience: Annotated[int | None, Query(ge=0, le=80)] = None,
) -> LeaderboardResponse:
    return await LeaderboardService(session).get(
        athlete_id=current_user.id,
        sport=sport,
        state=state,
        gender=gender,
        min_age=min_age,
        max_age=max_age,
        min_experience=min_experience,
        max_experience=max_experience,
    )


@router.get("/leaderboard/{upload_id}/results", response_model=AssessmentDetail)
async def leaderboard_assessment_results(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AssessmentDetail:
    try:
        return await AssessmentService(session).get_leaderboard(upload_id=upload_id)
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except AssessmentNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is not completed",
        ) from exc


@router.get("/leaderboard/{upload_id}/biomechanics", response_model=BiomechanicalMetrics)
async def leaderboard_stored_biomechanics(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BiomechanicalMetrics:
    try:
        return await StoredAnalysisService(session).calculate_leaderboard_biomechanics(
            upload_id=upload_id
        )
    except AnalysisUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except PoseProcessingRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pose processing must be completed first",
        ) from exc
    except NoPoseDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/leaderboard/{upload_id}/replay", response_model=CoachReplayTimeline)
async def leaderboard_coach_replay(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> CoachReplayTimeline:
    try:
        return await StoredAnalysisService(session).leaderboard_coach_replay(
            upload_id=upload_id
        )
    except AnalysisUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except PoseProcessingRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pose processing must be completed first",
        ) from exc
    except NoPoseDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/leaderboard/{upload_id}/report")
async def leaderboard_assessment_report(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Response:
    try:
        content, filename = await AssessmentReportService(session).for_leaderboard(
            upload_id=upload_id
        )
    except ReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed assessment report not found",
        ) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/leaderboard/{upload_id}/content", response_class=FileResponse)
async def leaderboard_uploaded_video_content(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_media_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FileResponse:
    try:
        upload = await AssessmentService(session).leaderboard_video(upload_id=upload_id)
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    video_path = Path(upload.temporary_path)
    if not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The uploaded video is no longer available",
        )
    return FileResponse(video_path, media_type=upload.content_type)


@router.get("/leaderboard/{upload_id}/annotated-content", response_class=FileResponse)
async def leaderboard_annotated_video_content(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_media_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FileResponse:
    try:
        upload = await AssessmentService(session).leaderboard_video(upload_id=upload_id)
        video_path = await VideoProcessingService(session).annotated_video(
            upload_id=upload_id, athlete_id=upload.athlete_id
        )
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except UploadedVideoMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The uploaded video is no longer available",
        ) from exc
    except (AnnotatedVideoUnavailableError, VisualizationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated analysis video is not available",
        ) from exc
    return FileResponse(video_path, media_type="video/mp4")


@router.get("/{upload_id}/replay", response_model=CoachReplayTimeline)
async def coach_replay(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> CoachReplayTimeline:
    try:
        return await StoredAnalysisService(session).coach_replay(
            upload_id=upload_id, athlete_id=current_user.id
        )
    except AnalysisUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except PoseProcessingRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pose processing must be completed first",
        ) from exc
    except NoPoseDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/{upload_id}/results", response_model=AssessmentDetail)
async def assessment_results(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AssessmentDetail:
    try:
        return await AssessmentService(session).get(
            upload_id=upload_id, athlete_id=current_user.id
        )
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except AssessmentNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is not completed",
        ) from exc


@router.get("/{upload_id}/report")
async def athlete_assessment_report(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> Response:
    try:
        content, filename = await AssessmentReportService(session).for_athlete(
            upload_id=upload_id, athlete_id=current_user.id
        )
    except ReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed assessment report not found",
        ) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{upload_id}/content", response_class=FileResponse)
async def uploaded_video_content(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_media_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FileResponse:
    try:
        upload = await AssessmentService(session).video(
            upload_id=upload_id, athlete_id=current_user.id
        )
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    video_path = Path(upload.temporary_path)
    if not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The uploaded video is no longer available",
        )
    return FileResponse(video_path, media_type=upload.content_type)


@router.get("/{upload_id}/annotated-content", response_class=FileResponse)
async def annotated_video_content(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_media_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> FileResponse:
    try:
        video_path = await VideoProcessingService(session).annotated_video(
            upload_id=upload_id, athlete_id=current_user.id
        )
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    except UploadedVideoMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The uploaded video is no longer available",
        ) from exc
    except (AnnotatedVideoUnavailableError, VisualizationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated analysis video is not available",
        ) from exc
    return FileResponse(video_path, media_type="video/mp4")


@router.post("/{upload_id}/assessment", response_model=RecommendationResult)
async def create_assessment(
    upload_id: uuid.UUID,
    scores: BenchmarkScores,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> RecommendationResult:
    try:
        return await AssessmentService(session).create(
            upload_id=upload_id,
            athlete_id=current_user.id,
            scores=scores,
        )
    except AssessmentUploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        ) from exc


@router.post("/{upload_id}/process", response_model=VideoProcessingResponse)
async def process_video(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> VideoProcessingResponse:
    try:
        return await VideoProcessingService(session).process(
            upload_id=upload_id,
            athlete_id=current_user.id,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        ) from exc
    except UploadedVideoMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The uploaded video is no longer available",
        ) from exc
    except PoseExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except VisualizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except VideoQualityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(
    file: Annotated[UploadFile, File()],
    sport: Annotated[Sport, Form()],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> VideoUploadResponse:
    try:
        return await VideoUploadService(session).upload(
            athlete_id=current_user.id,
            sport=sport,
            file=file,
        )
    except UnsupportedVideoTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only MP4, MOV, and WebM videos are supported",
        ) from exc
    except EmptyVideoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded video is empty",
        ) from exc
    except VideoTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Video size must not exceed 200 MB",
        ) from exc
    finally:
        await file.close()
