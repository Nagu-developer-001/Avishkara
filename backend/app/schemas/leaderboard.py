import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    rank: int = Field(ge=1)
    athlete_id: uuid.UUID
    assessment_id: uuid.UUID
    upload_id: uuid.UUID
    name: str
    sport: str
    state: str
    overall_score: float = Field(ge=0, le=100)
    technique_score: float = Field(ge=0, le=100)
    efficiency_score: float = Field(ge=0, le=100)
    balance_score: float = Field(ge=0, le=100)
    completed_at: datetime
    is_current_user: bool


class LeaderboardResponse(BaseModel):
    top_athletes: list[LeaderboardEntry]
    current_user_entry: LeaderboardEntry | None = None
