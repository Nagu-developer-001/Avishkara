import json
import uuid
from pathlib import Path

import cv2
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pose_processing import PoseProcessingResult
from app.models.video import VideoUpload
from app.constants.upload import REJECTED_STATUS
from app.schemas.pose import FullVideoPoseResult, PoseLandmark, ProcessedPoseFrame
from app.schemas.processing import VideoProcessingResponse
from app.services.biomechanical_visualization import (
    BiomechanicalVisualizationService,
)
from app.services.mediapipe_pose import MediaPipePoseService
from app.services.video_quality import VideoQualityError, VideoQualityService
from app.utils.config import settings


class UploadNotFoundError(LookupError):
    pass


class UploadedVideoMissingError(FileNotFoundError):
    pass


class AnnotatedVideoUnavailableError(FileNotFoundError):
    pass


class VideoProcessingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def process(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> VideoProcessingResponse:
        upload = await self._load_upload(upload_id, athlete_id)
        video_path = Path(upload.temporary_path)
        if not video_path.is_file():
            raise UploadedVideoMissingError(video_path)

        pose_result = await run_in_threadpool(
            MediaPipePoseService().extract_all, video_path
        )
        quality = VideoQualityService().validate(pose_result, upload.sport)
        if not quality.valid:
            upload.status = REJECTED_STATUS
            await self.session.commit()
            raise VideoQualityError(quality.reasons)
        landmark_path = self._landmark_path(athlete_id, upload_id)
        payload = {
            "uploadId": str(upload_id),
            "totalFrames": pose_result.total_frames,
            "processedFrames": pose_result.processed_frames,
            "frames": [
                {
                    "frameIndex": frame.frame_index,
                    "timestampMs": frame.timestamp_ms,
                    "landmarks": [
                        landmark.model_dump() for landmark in frame.landmarks
                    ],
                }
                for frame in pose_result.frames
            ],
        }
        await run_in_threadpool(self._write_json, landmark_path, payload)
        annotated_path = self._annotated_path(athlete_id, upload_id)
        if settings.generate_annotated_video:
            try:
                await run_in_threadpool(
                    BiomechanicalVisualizationService().generate,
                    video_path=video_path,
                    pose_result=pose_result,
                    output_path=annotated_path,
                )
            except Exception:
                annotated_path.unlink(missing_ok=True)

        await self._save_result(
            upload_id=upload_id,
            total_frames=pose_result.total_frames,
            processed_frames=pose_result.processed_frames,
            landmark_path=landmark_path,
        )
        return VideoProcessingResponse(
            upload_id=upload_id,
            total_frames=pose_result.total_frames,
            processed_frames=pose_result.processed_frames,
            landmark_file=str(landmark_path),
        )

    async def annotated_video(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> Path:
        upload = await self._load_upload(upload_id, athlete_id)
        annotated_path = self._annotated_path(athlete_id, upload_id)
        if await run_in_threadpool(self._is_readable_video, annotated_path):
            return annotated_path

        video_path = Path(upload.temporary_path)
        if not video_path.is_file():
            raise UploadedVideoMissingError(video_path)

        pose_result = await self._load_pose_result(upload_id=upload_id)
        if pose_result is None:
            raise AnnotatedVideoUnavailableError(annotated_path)

        await run_in_threadpool(
            BiomechanicalVisualizationService().generate,
            video_path=video_path,
            pose_result=pose_result,
            output_path=annotated_path,
        )
        if not await run_in_threadpool(self._is_readable_video, annotated_path):
            raise AnnotatedVideoUnavailableError(annotated_path)
        return annotated_path

    async def _load_upload(
        self, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> VideoUpload:
        result = await self.session.execute(
            select(VideoUpload).where(
                VideoUpload.id == upload_id,
                VideoUpload.athlete_id == athlete_id,
            )
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise UploadNotFoundError(upload_id)
        return upload

    async def _save_result(
        self,
        *,
        upload_id: uuid.UUID,
        total_frames: int,
        processed_frames: int,
        landmark_path: Path,
    ) -> None:
        result = await self.session.execute(
            select(PoseProcessingResult).where(
                PoseProcessingResult.upload_id == upload_id
            )
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            stored = PoseProcessingResult(upload_id=upload_id)
            self.session.add(stored)
        stored.total_frames = total_frames
        stored.processed_frames = processed_frames
        stored.landmark_file = str(landmark_path)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            landmark_path.unlink(missing_ok=True)
            raise

    async def _load_pose_result(
        self, *, upload_id: uuid.UUID
    ) -> FullVideoPoseResult | None:
        result = await self.session.execute(
            select(PoseProcessingResult).where(
                PoseProcessingResult.upload_id == upload_id
            )
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            return None
        landmark_path = Path(stored.landmark_file)
        if not landmark_path.is_file():
            return None
        return await run_in_threadpool(
            self._read_pose_result,
            landmark_path,
            stored.total_frames,
            stored.processed_frames,
        )

    @staticmethod
    def _landmark_path(athlete_id: uuid.UUID, upload_id: uuid.UUID) -> Path:
        return (
            settings.landmark_directory
            / VideoProcessingService._uuid_folder(athlete_id)
            / f"{upload_id}.json"
        )

    @staticmethod
    def annotated_path(athlete_id: uuid.UUID, upload_id: uuid.UUID) -> Path:
        return VideoProcessingService._annotated_path(athlete_id, upload_id)

    @staticmethod
    def _annotated_path(athlete_id: uuid.UUID, upload_id: uuid.UUID) -> Path:
        return (
            settings.annotated_video_directory
            / VideoProcessingService._uuid_folder(athlete_id)
            / f"{upload_id}.mp4"
        )

    @staticmethod
    def _uuid_folder(value: uuid.UUID | str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except ValueError:
            return str(value)

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8"
        )
        temporary_path.replace(path)

    @staticmethod
    def _read_pose_result(
        path: Path, total_frames: int, processed_frames: int
    ) -> FullVideoPoseResult:
        payload = json.loads(path.read_text(encoding="utf-8"))
        frames = [
            ProcessedPoseFrame(
                frame_index=frame["frameIndex"],
                timestamp_ms=frame["timestampMs"],
                landmarks=[
                    PoseLandmark.model_validate(landmark)
                    for landmark in frame.get("landmarks", [])
                ],
            )
            for frame in payload.get("frames", [])
        ]
        fps = VideoProcessingService._estimate_fps(frames)
        return FullVideoPoseResult(
            fps=fps,
            total_frames=int(payload.get("totalFrames", total_frames)),
            processed_frames=int(payload.get("processedFrames", processed_frames)),
            frames=frames,
        )

    @staticmethod
    def _estimate_fps(frames: list[ProcessedPoseFrame]) -> float:
        if len(frames) >= 2:
            first = frames[0].timestamp_ms
            last = frames[-1].timestamp_ms
            duration_ms = last - first
            if duration_ms > 0:
                return max(1.0, (len(frames) - 1) * 1000 / duration_ms)
        return 30.0

    @staticmethod
    def _is_readable_video(path: Path) -> bool:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        capture = cv2.VideoCapture(str(path))
        try:
            success, _ = capture.read()
            fourcc_number = int(capture.get(cv2.CAP_PROP_FOURCC))
            codec = "".join(
                chr((fourcc_number >> 8 * index) & 0xFF) for index in range(4)
            ).strip().lower()
            return bool(success) and codec in {"h264", "avc1"}
        finally:
            capture.release()
