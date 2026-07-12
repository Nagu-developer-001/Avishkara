import uuid
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class Sport(StrEnum):
    RUNNING = "Running"
    JUMPING = "Jumping"
    BOWLING = "Bowling"


class VideoUploadResponse(BaseModel):
    upload_id: uuid.UUID
    status: Literal["Uploaded"]
