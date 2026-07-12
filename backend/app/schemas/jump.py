from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Point2D(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    visibility: float = Field(default=1, ge=0, le=1)


class PoseFrame(BaseModel):
    frame_index: int = Field(ge=0)
    landmarks: dict[str, Point2D]


class JumpAnalysisRequest(BaseModel):
    fps: float = Field(gt=0, le=240)
    athlete_height_m: float = Field(gt=0.8, le=2.5)
    frames: list[PoseFrame] = Field(min_length=12)

    @model_validator(mode="after")
    def validate_frame_order(self) -> "JumpAnalysisRequest":
        indexes = [frame.frame_index for frame in self.frames]
        if indexes != sorted(indexes) or len(indexes) != len(set(indexes)):
            raise ValueError("frame_index values must be unique and increasing")
        return self


class Metric(BaseModel):
    value: float
    unit: str
    confidence: float = Field(ge=0, le=1)
    method: str


class Finding(BaseModel):
    category: Literal["strength", "improvement", "warning"]
    title: str
    detail: str


class JumpAnalysisResult(BaseModel):
    activity: Literal["vertical_jump"] = "vertical_jump"
    takeoff_frame: int
    landing_frame: int
    metrics: dict[str, Metric]
    biomechanics_score: float = Field(ge=0, le=100)
    score_components: dict[str, float]
    findings: list[Finding]
    limitations: list[str]
