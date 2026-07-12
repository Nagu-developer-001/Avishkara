import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProgressTrendPoint(BaseModel):
    upload_id: uuid.UUID
    sport: str
    upload_time: datetime
    overall_score: float = Field(ge=0, le=100)
    technique_score: float = Field(ge=0, le=100)
    efficiency_score: float = Field(ge=0, le=100)
    balance_score: float = Field(ge=0, le=100)


class AthleteProgressAnalytics(BaseModel):
    assessment_count: int = Field(ge=0)
    average_score: float | None = Field(default=None, ge=0, le=100)
    best_score: float | None = Field(default=None, ge=0, le=100)
    improvement: float | None = None
    trend: list[ProgressTrendPoint]
