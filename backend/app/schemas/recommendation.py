import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.benchmark import BenchmarkScores


class RecommendationResult(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    improvement_suggestions: list[str]

    @property
    def suggestions(self) -> list[str]:
        return self.improvement_suggestions


class AssessmentVideo(BaseModel):
    upload_id: uuid.UUID
    filename: str
    sport: str
    upload_time: datetime
    status: str
    content_type: str


class AssessmentDetail(BaseModel):
    video: AssessmentVideo
    scores: BenchmarkScores
    recommendations: RecommendationResult


class AssessmentHistoryItem(BaseModel):
    upload_id: uuid.UUID
    filename: str
    sport: str
    upload_time: datetime
    overall_score: float | None
