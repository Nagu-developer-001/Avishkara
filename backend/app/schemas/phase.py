from pydantic import BaseModel, Field


class DetectedPhase(BaseModel):
    name: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    frame_indexes: list[int] = Field(min_length=1)
