import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import UPLOAD_STATUS
from app.models.video import VideoUpload
from app.schemas.video import Sport, VideoUploadResponse
from app.services.video_storage import VideoStorageService


class VideoUploadService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upload(
        self,
        *,
        athlete_id: uuid.UUID,
        sport: Sport,
        file: UploadFile,
    ) -> VideoUploadResponse:
        upload_id = uuid.uuid4()
        stored = await VideoStorageService().store(
            file=file,
            athlete_id=athlete_id,
            upload_id=upload_id,
        )
        upload = VideoUpload(
            id=upload_id,
            athlete_id=athlete_id,
            sport=sport.value,
            filename=stored.filename,
            status=UPLOAD_STATUS,
            content_type=stored.content_type,
            file_size_bytes=stored.size_bytes,
            temporary_path=str(stored.path),
        )
        self.session.add(upload)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            Path(stored.path).unlink(missing_ok=True)
            raise

        return VideoUploadResponse(upload_id=upload.id, status="Uploaded")
