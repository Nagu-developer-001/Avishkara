from pydantic import BaseModel, Field, field_validator


class PoseLandmark(BaseModel):
    index: int = Field(ge=0, le=32)
    name: str
    x: float
    y: float
    z: float
    visibility: float | None = None
    presence: float | None = None


class PoseFrame(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    landmarks: list[PoseLandmark] = Field(min_length=33, max_length=33)


class VideoPoseResult(BaseModel):
    fps: float = Field(gt=0)
    processed_frames: int = Field(ge=0)
    detected_frames: int = Field(ge=0)
    frames: list[PoseFrame]


class ProcessedPoseFrame(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    landmarks: list[PoseLandmark] = Field(max_length=33)

    @field_validator("landmarks")
    @classmethod
    def validate_landmark_count(
        cls, landmarks: list[PoseLandmark]
    ) -> list[PoseLandmark]:
        if len(landmarks) not in (0, 33):
            raise ValueError("A frame must contain zero or 33 pose landmarks")
        return landmarks


class FullVideoPoseResult(BaseModel):
    fps: float = Field(gt=0)
    total_frames: int = Field(ge=0)
    processed_frames: int = Field(ge=0)
    frames: list[ProcessedPoseFrame]
