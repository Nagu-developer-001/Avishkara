import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import COMPLETED_STATUS
from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.video import VideoUpload
from app.schemas.benchmark import BenchmarkScores
from app.schemas.recommendation import (
    AssessmentDetail,
    AssessmentHistoryItem,
    AssessmentVideo,
    RecommendationResult,
)
from app.services.recommendation import RecommendationEngine


class AssessmentUploadNotFoundError(LookupError):
    pass


class AssessmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        upload_id: uuid.UUID,
        athlete_id: uuid.UUID,
        scores: BenchmarkScores,
    ) -> RecommendationResult:
        upload = await self._load_upload(upload_id, athlete_id)
        recommendation = RecommendationEngine().generate(scores)
        assessment = await self._load_assessment(upload_id)
        snapshot = await self._load_snapshot(upload_id)
        if assessment is None:
            assessment = Assessment(upload_id=upload_id)
            self.session.add(assessment)
        if snapshot is None:
            snapshot = AssessmentSnapshot(upload_id=upload_id)
            self.session.add(snapshot)

        assessment.strengths = recommendation.strengths
        assessment.weaknesses = recommendation.weaknesses
        assessment.improvement_suggestions = (
            recommendation.improvement_suggestions
        )
        snapshot.benchmark_result = scores.model_dump(mode="json")
        upload.status = COMPLETED_STATUS

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return recommendation

    async def get(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> AssessmentDetail:
        upload = await self._load_upload(upload_id, athlete_id)
        return await self._detail(upload)

    async def get_leaderboard(self, *, upload_id: uuid.UUID) -> AssessmentDetail:
        upload = await self._load_completed_upload(upload_id)
        return await self._detail(upload)

    async def _detail(self, upload: VideoUpload) -> AssessmentDetail:
        assessment = await self._load_assessment(upload.id)
        snapshot = await self._load_snapshot(upload.id)
        if assessment is None or snapshot is None:
            raise AssessmentNotReadyError(upload.id)
        return AssessmentDetail(
            video=AssessmentVideo(
                upload_id=upload.id,
                filename=upload.filename,
                sport=upload.sport,
                upload_time=upload.upload_time,
                status=upload.status,
                content_type=upload.content_type,
            ),
            scores=BenchmarkScores.model_validate(snapshot.benchmark_result),
            recommendations=RecommendationResult(
                strengths=assessment.strengths,
                weaknesses=assessment.weaknesses,
                improvement_suggestions=assessment.improvement_suggestions,
            ),
        )

    async def history(self, *, athlete_id: uuid.UUID) -> list[AssessmentHistoryItem]:
        result = await self.session.execute(
            select(VideoUpload, AssessmentSnapshot)
            .join(
                AssessmentSnapshot,
                AssessmentSnapshot.upload_id == VideoUpload.id,
            )
            .where(
                VideoUpload.athlete_id == athlete_id,
                VideoUpload.status == COMPLETED_STATUS,
            )
            .order_by(VideoUpload.upload_time.desc())
        )
        return [
            AssessmentHistoryItem(
                upload_id=upload.id,
                filename=upload.filename,
                sport=upload.sport,
                upload_time=upload.upload_time,
                overall_score=BenchmarkScores.model_validate(
                    snapshot.benchmark_result
                ).overall_score,
            )
            for upload, snapshot in result.all()
        ]

    async def video(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> VideoUpload:
        return await self._load_upload(upload_id, athlete_id)

    async def leaderboard_video(self, *, upload_id: uuid.UUID) -> VideoUpload:
        return await self._load_completed_upload(upload_id)

    async def _load_upload(
        self, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> VideoUpload:
        result = await self.session.execute(
            select(VideoUpload).where(
                VideoUpload.id == upload_id,
                VideoUpload.athlete_id == athlete_id,
            )
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise AssessmentUploadNotFoundError(upload_id)
        return upload

    async def _load_completed_upload(self, upload_id: uuid.UUID) -> VideoUpload:
        result = await self.session.execute(
            select(VideoUpload).where(
                VideoUpload.id == upload_id,
                VideoUpload.status == COMPLETED_STATUS,
            )
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise AssessmentUploadNotFoundError(upload_id)
        return upload

    async def _load_assessment(
        self, upload_id: uuid.UUID
    ) -> Assessment | None:
        result = await self.session.execute(
            select(Assessment).where(Assessment.upload_id == upload_id)
        )
        return result.scalar_one_or_none()

    async def _load_snapshot(
        self, upload_id: uuid.UUID
    ) -> AssessmentSnapshot | None:
        result = await self.session.execute(
            select(AssessmentSnapshot).where(
                AssessmentSnapshot.upload_id == upload_id
            )
        )
        return result.scalar_one_or_none()


class AssessmentNotReadyError(LookupError):
    pass
