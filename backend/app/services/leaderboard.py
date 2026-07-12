import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import COMPLETED_STATUS
from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.athlete_profile import AthleteProfile
from app.models.user import User
from app.models.video import VideoUpload
from app.schemas.benchmark import BenchmarkScores
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse


SPORT_FILTER_ALIASES = {
    "bowling": ("Bowling", "Cricket Bowling"),
    "cricket bowling": ("Bowling", "Cricket Bowling"),
}


class LeaderboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self,
        *,
        athlete_id: uuid.UUID,
        sport: str | None = None,
        state: str | None = None,
        gender: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_experience: int | None = None,
        max_experience: int | None = None,
    ) -> LeaderboardResponse:
        filters = []
        if sport:
            filters.append(VideoUpload.sport.in_(self._sport_filter_values(sport)))
        if state:
            filters.append(AthleteProfile.state == state)
        if gender:
            filters.append(AthleteProfile.gender == gender)
        if min_age is not None:
            filters.append(AthleteProfile.age >= min_age)
        if max_age is not None:
            filters.append(AthleteProfile.age <= max_age)
        if min_experience is not None:
            filters.append(AthleteProfile.experience >= min_experience)
        if max_experience is not None:
            filters.append(AthleteProfile.experience <= max_experience)

        result = await self.session.execute(
            select(
                User,
                AthleteProfile,
                VideoUpload,
                Assessment,
                AssessmentSnapshot,
            )
            .join(AthleteProfile, AthleteProfile.user_id == User.id)
            .join(VideoUpload, VideoUpload.athlete_id == User.id)
            .join(Assessment, Assessment.upload_id == VideoUpload.id)
            .join(AssessmentSnapshot, AssessmentSnapshot.upload_id == VideoUpload.id)
            .where(VideoUpload.status == COMPLETED_STATUS)
            .where(*filters)
            .order_by(VideoUpload.upload_time.desc())
        )

        current_athlete_id = self._uuid(athlete_id)
        best_by_athlete: dict[uuid.UUID, LeaderboardEntry] = {}

        for user, profile, upload, assessment, snapshot in result.all():
            scores = BenchmarkScores.model_validate(snapshot.benchmark_result)
            if scores.overall_score is None:
                continue

            normalized_athlete_id = self._uuid(user.id)
            candidate = LeaderboardEntry(
                rank=1,
                athlete_id=normalized_athlete_id,
                assessment_id=self._uuid(assessment.id),
                upload_id=self._uuid(upload.id),
                name=user.name,
                sport=upload.sport,
                state=profile.state,
                overall_score=round(scores.overall_score, 2),
                technique_score=round(scores.technique_score, 2),
                efficiency_score=round(scores.efficiency_score, 2),
                balance_score=round(scores.balance_score, 2),
                completed_at=upload.upload_time,
                is_current_user=normalized_athlete_id == current_athlete_id,
            )
            existing = best_by_athlete.get(normalized_athlete_id)
            if existing is None or self._is_better(candidate, existing):
                best_by_athlete[normalized_athlete_id] = candidate

        ranked = sorted(
            best_by_athlete.values(),
            key=lambda item: (-item.overall_score, item.completed_at),
        )
        for index, item in enumerate(ranked, start=1):
            item.rank = index

        top_athletes = ranked[:5]
        current_user_entry = next(
            (
                item
                for item in ranked
                if item.athlete_id == current_athlete_id and item.rank > 5
            ),
            None,
        )
        return LeaderboardResponse(
            top_athletes=top_athletes,
            current_user_entry=current_user_entry,
        )

    @staticmethod
    def _is_better(candidate: LeaderboardEntry, existing: LeaderboardEntry) -> bool:
        if candidate.overall_score != existing.overall_score:
            return candidate.overall_score > existing.overall_score
        return candidate.completed_at > existing.completed_at

    @staticmethod
    def _uuid(value: uuid.UUID | str) -> uuid.UUID:
        return uuid.UUID(str(value))

    @staticmethod
    def _sport_filter_values(sport: str) -> tuple[str, ...]:
        normalized = " ".join(sport.strip().casefold().split())
        return SPORT_FILTER_ALIASES.get(normalized, (sport,))
