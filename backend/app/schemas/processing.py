import uuid

from pydantic import BaseModel, ConfigDict, Field


class VideoProcessingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    upload_id: uuid.UUID = Field(serialization_alias="uploadId")
    total_frames: int = Field(serialization_alias="totalFrames", ge=0)
    processed_frames: int = Field(serialization_alias="processedFrames", ge=0)
    landmark_file: str = Field(serialization_alias="landmarkFile")
