import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import COMPLETED_STATUS
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.video import VideoUpload
from app.schemas.benchmark import BenchmarkScores
from app.schemas.progress import AthleteProgressAnalytics, ProgressTrendPoint


class ProgressAnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, *, athlete_id: uuid.UUID) -> AthleteProgressAnalytics:
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
            .order_by(VideoUpload.upload_time.asc())
        )

        trend: list[ProgressTrendPoint] = []
        for upload, snapshot in result.all():
            scores = BenchmarkScores.model_validate(snapshot.benchmark_result)
            if scores.overall_score is None:
                continue
            trend.append(
                ProgressTrendPoint(
                    upload_id=upload.id,
                    sport=upload.sport,
                    upload_time=upload.upload_time,
                    overall_score=scores.overall_score,
                    technique_score=scores.technique_score,
                    efficiency_score=scores.efficiency_score,
                    balance_score=scores.balance_score,
                )
            )

        if not trend:
            return AthleteProgressAnalytics(
                assessment_count=0,
                average_score=None,
                best_score=None,
                improvement=None,
                trend=[],
            )

        overall_scores = [point.overall_score for point in trend]
        return AthleteProgressAnalytics(
            assessment_count=len(trend),
            average_score=round(sum(overall_scores) / len(overall_scores), 2),
            best_score=round(max(overall_scores), 2),
            improvement=round(overall_scores[-1] - overall_scores[0], 2),
            trend=trend,
        )
