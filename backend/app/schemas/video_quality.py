from pydantic import BaseModel


class VideoQualityResult(BaseModel):
    valid: bool
    reasons: list[str]
    detected_frames: int
    full_body_frames: int
