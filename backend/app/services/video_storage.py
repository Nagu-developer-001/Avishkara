import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.constants.upload import (
    ACCEPTED_VIDEO_TYPES,
    MAX_VIDEO_SIZE_BYTES,
    UPLOAD_CHUNK_SIZE_BYTES,
)
from app.utils.config import settings


class UnsupportedVideoTypeError(ValueError):
    pass


class EmptyVideoError(ValueError):
    pass


class VideoTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class StoredVideo:
    path: Path
    filename: str
    content_type: str
    size_bytes: int


class VideoStorageService:
    async def store(
        self,
        *,
        file: UploadFile,
        athlete_id: uuid.UUID,
        upload_id: uuid.UUID,
    ) -> StoredVideo:
        content_type = file.content_type or ""
        expected_extension = ACCEPTED_VIDEO_TYPES.get(content_type)
        filename = Path(file.filename or "video").name[:255]
        extension = Path(filename).suffix.lower()

        if expected_extension is None or extension != expected_extension:
            raise UnsupportedVideoTypeError
        if file.size is not None and file.size > MAX_VIDEO_SIZE_BYTES:
            raise VideoTooLargeError

        athlete_directory = settings.upload_directory / str(athlete_id)
        athlete_directory.mkdir(parents=True, exist_ok=True)
        destination = athlete_directory / f"{upload_id}{extension}"
        size_bytes = 0

        try:
            with destination.open("wb") as stored_file:
                while chunk := await file.read(UPLOAD_CHUNK_SIZE_BYTES):
                    size_bytes += len(chunk)
                    if size_bytes > MAX_VIDEO_SIZE_BYTES:
                        raise VideoTooLargeError
                    stored_file.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        if size_bytes == 0:
            destination.unlink(missing_ok=True)
            raise EmptyVideoError

        return StoredVideo(
            path=destination,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
