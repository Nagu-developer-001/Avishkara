import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import COMPLETED_STATUS
from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.athlete_profile import AthleteProfile
from app.models.shortlist import AthleteShortlist
from app.models.user import User
from app.models.video import VideoUpload
from app.schemas.authority import (
    AuthorityAssessmentDetail,
    AuthorityAssessmentSummary,
    AuthorityAthleteItem,
    AuthorityAthleteProfile,
    AuthorityDashboardResponse,
    AuthoritySummary,
    AuthorityVideo,
    ShortlistDetail,
    ShortlistResponse,
)
from app.schemas.benchmark import BenchmarkScores
from app.schemas.recommendation import RecommendationResult
from app.services.video_processing import VideoProcessingService


class AuthorityAssessmentNotFoundError(LookupError):
    pass


class AuthorityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def dashboard(
        self,
        *,
        sport: str | None = None,
        state: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        shortlisted: bool | None = None,
    ) -> AuthorityDashboardResponse:
        records = await self._assessment_records()
        shortlist_ids = await self._shortlisted_assessment_ids()
        scores = [record[5].overall_score for record in records if record[5].overall_score is not None]
        athlete_count = await self.session.scalar(select(func.count(AthleteProfile.id)))

        recent = [
            AuthorityAssessmentSummary(
                assessment_id=assessment.id,
                athlete_id=user.id,
                athlete_name=user.name,
                sport=upload.sport,
                completed_at=assessment.updated_at,
                overall_score=score.overall_score,
            )
            for user, _, upload, assessment, _, score in records[:5]
            if score.overall_score is not None
        ]

        latest_by_athlete: dict[uuid.UUID, tuple] = {}
        for record in records:
            user = record[0]
            latest_by_athlete.setdefault(user.id, record)

        athletes: list[AuthorityAthleteItem] = []
        for user, profile, upload, assessment, _, score in latest_by_athlete.values():
            if score.overall_score is None:
                continue
            is_shortlisted = assessment.id in shortlist_ids
            if sport and upload.sport.casefold() != sport.casefold():
                continue
            if state and profile.state.casefold() != state.casefold():
                continue
            if min_age is not None and profile.age < min_age:
                continue
            if max_age is not None and profile.age > max_age:
                continue
            if min_score is not None and score.overall_score < min_score:
                continue
            if max_score is not None and score.overall_score > max_score:
                continue
            if shortlisted is not None and is_shortlisted != shortlisted:
                continue
            athletes.append(
                AuthorityAthleteItem(
                    athlete_id=user.id,
                    assessment_id=assessment.id,
                    name=user.name,
                    sport=upload.sport,
                    state=profile.state,
                    age=profile.age,
                    latest_score=score.overall_score,
                    completed_at=assessment.updated_at,
                    shortlisted=is_shortlisted,
                )
            )

        return AuthorityDashboardResponse(
            summary=AuthoritySummary(
                total_athletes=athlete_count or 0,
                total_assessments=len(records),
                average_overall_score=(
                    round(sum(scores) / len(scores), 2) if scores else None
                ),
            ),
            recent_assessments=recent,
            athletes=athletes,
        )

    async def assessment(self, assessment_id: uuid.UUID) -> AuthorityAssessmentDetail:
        record = await self._assessment_record(assessment_id)
        if record is None:
            raise AuthorityAssessmentNotFoundError(assessment_id)
        user, profile, upload, assessment, stored, score = record
        shortlist = await self._shortlist(assessment.id)
        return AuthorityAssessmentDetail(
            assessment_id=assessment.id,
            athlete=AuthorityAthleteProfile(
                athlete_id=user.id,
                name=user.name,
                age=profile.age,
                gender=profile.gender,
                state=profile.state,
                sport=profile.sport,
                experience=profile.experience,
            ),
            video=AuthorityVideo(
                upload_id=upload.id,
                filename=upload.filename,
                sport=upload.sport,
                upload_time=upload.upload_time,
                annotated_available=VideoProcessingService.annotated_path(
                    user.id, upload.id
                ).is_file(),
            ),
            scores=score,
            recommendations=RecommendationResult(
                strengths=assessment.strengths,
                weaknesses=assessment.weaknesses,
                improvement_suggestions=assessment.improvement_suggestions,
            ),
            shortlist=ShortlistDetail(
                shortlisted=shortlist is not None,
                shortlisted_at=shortlist.shortlisted_at if shortlist else None,
                remarks=shortlist.remarks if shortlist else None,
            ),
        )

    async def shortlist(
        self,
        *,
        assessment_id: uuid.UUID,
        authority_id: uuid.UUID,
        remarks: str | None,
    ) -> ShortlistResponse:
        record = await self._assessment_record(assessment_id)
        if record is None:
            raise AuthorityAssessmentNotFoundError(assessment_id)
        user, _, _, assessment, _, _ = record
        stored = await self._shortlist(assessment.id)
        if stored is None:
            stored = AthleteShortlist(
                athlete_id=user.id,
                assessment_id=assessment.id,
                authority_id=authority_id,
                remarks=remarks,
            )
            self.session.add(stored)
        else:
            stored.remarks = remarks
            stored.authority_id = authority_id
        await self.session.commit()
        await self.session.refresh(stored)
        return ShortlistResponse(
            athlete_id=stored.athlete_id,
            assessment_id=stored.assessment_id,
            shortlisted_at=stored.shortlisted_at,
            remarks=stored.remarks,
        )

    async def video(self, assessment_id: uuid.UUID) -> tuple[Path, str]:
        record = await self._assessment_record(assessment_id)
        if record is None:
            raise AuthorityAssessmentNotFoundError(assessment_id)
        _, _, upload, _, _, _ = record
        return Path(upload.temporary_path), upload.content_type

    async def annotated_video(self, assessment_id: uuid.UUID) -> Path:
        record = await self._assessment_record(assessment_id)
        if record is None:
            raise AuthorityAssessmentNotFoundError(assessment_id)
        user, _, upload, _, _, _ = record
        return await VideoProcessingService(self.session).annotated_video(
            upload_id=upload.id,
            athlete_id=user.id,
        )

    async def _assessment_records(self) -> list[tuple]:
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
            .order_by(Assessment.updated_at.desc())
        )
        return [
            (*row, BenchmarkScores.model_validate(row[4].benchmark_result))
            for row in result.all()
        ]

    async def _assessment_record(self, assessment_id: uuid.UUID) -> tuple | None:
        records = await self._assessment_records()
        return next((record for record in records if record[3].id == assessment_id), None)

    async def _shortlisted_assessment_ids(self) -> set[uuid.UUID]:
        result = await self.session.execute(select(AthleteShortlist.assessment_id))
        return set(result.scalars().all())

    async def _shortlist(self, assessment_id: uuid.UUID) -> AthleteShortlist | None:
        result = await self.session.execute(
            select(AthleteShortlist).where(
                AthleteShortlist.assessment_id == assessment_id
            )
        )
        return result.scalar_one_or_none()
