import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.benchmark import BenchmarkScores
from app.schemas.recommendation import RecommendationResult


class AuthoritySummary(BaseModel):
    total_athletes: int = Field(ge=0)
    total_assessments: int = Field(ge=0)
    average_overall_score: float | None = Field(default=None, ge=0, le=100)


class AuthorityAssessmentSummary(BaseModel):
    assessment_id: uuid.UUID
    athlete_id: uuid.UUID
    athlete_name: str
    sport: str
    completed_at: datetime
    overall_score: float


class AuthorityAthleteItem(BaseModel):
    athlete_id: uuid.UUID
    assessment_id: uuid.UUID
    name: str
    sport: str
    state: str
    age: int
    latest_score: float
    completed_at: datetime
    shortlisted: bool


class AuthorityDashboardResponse(BaseModel):
    summary: AuthoritySummary
    recent_assessments: list[AuthorityAssessmentSummary]
    athletes: list[AuthorityAthleteItem]


class NationalLeaderboardItem(BaseModel):
    rank: int = Field(ge=1)
    athlete_id: uuid.UUID
    assessment_id: uuid.UUID
    name: str
    sport: str
    state: str
    age: int
    overall_score: float = Field(ge=0, le=100)
    technique_score: float = Field(ge=0, le=100)
    efficiency_score: float = Field(ge=0, le=100)
    balance_score: float = Field(ge=0, le=100)
    completed_at: datetime
    shortlisted: bool


class NationalLeaderboardResponse(BaseModel):
    athletes: list[NationalLeaderboardItem]


class AuthorityAthleteProfile(BaseModel):
    athlete_id: uuid.UUID
    name: str
    age: int
    gender: str
    state: str
    sport: str
    experience: int


class AuthorityVideo(BaseModel):
    upload_id: uuid.UUID
    filename: str
    sport: str
    upload_time: datetime
    annotated_available: bool


class ShortlistDetail(BaseModel):
    shortlisted: bool
    shortlisted_at: datetime | None = None
    remarks: str | None = None


class AuthorityAssessmentDetail(BaseModel):
    assessment_id: uuid.UUID
    athlete: AuthorityAthleteProfile
    video: AuthorityVideo
    scores: BenchmarkScores
    recommendations: RecommendationResult
    shortlist: ShortlistDetail


class ShortlistRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=1000)

    @field_validator("remarks")
    @classmethod
    def normalize_remarks(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ShortlistResponse(BaseModel):
    athlete_id: uuid.UUID
    assessment_id: uuid.UUID
    shortlisted_at: datetime
    remarks: str | None
