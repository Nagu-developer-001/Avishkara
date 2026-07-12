from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import (
    FullVideoPoseResult,
    PoseFrame,
    PoseLandmark,
    ProcessedPoseFrame,
    VideoPoseResult,
)
from app.utils.config import settings


class PoseExtractionError(ValueError):
    pass


class MediaPipePoseService:
    def __init__(self, model_path: Path | None = None):
        self.model_path = model_path or settings.pose_landmarker_model_path

    def extract(self, video_path: Path) -> VideoPoseResult:
        result = self.extract_all(video_path)
        detected_frames = [
            PoseFrame(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                landmarks=frame.landmarks,
            )
            for frame in result.frames
            if frame.landmarks
        ]
        return VideoPoseResult(
            fps=result.fps,
            processed_frames=result.processed_frames,
            detected_frames=len(detected_frames),
            frames=detected_frames,
        )

    def extract_all(self, video_path: Path) -> FullVideoPoseResult:
        if not video_path.is_file():
            raise PoseExtractionError(f"Video file does not exist: {video_path}")
        if not self.model_path.is_file():
            raise PoseExtractionError(
                f"MediaPipe pose model does not exist: {self.model_path}"
            )

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            raise PoseExtractionError(f"Unable to open video: {video_path}")

        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if not np.isfinite(fps) or fps <= 0:
            capture.release()
            raise PoseExtractionError("Video does not contain a valid frame rate")

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(self.model_path)
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            output_segmentation_masks=False,
        )

        frames: list[ProcessedPoseFrame] = []
        frame_index = 0
        try:
            with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
                while True:
                    success, frame = capture.read()
                    if not success:
                        break

                    timestamp_ms = round(frame_index * 1000 / fps)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=np.ascontiguousarray(rgb_frame),
                    )
                    result = landmarker.detect_for_video(image, timestamp_ms)
                    landmarks = (
                        self._serialize_landmarks(result.pose_landmarks[0])
                        if result.pose_landmarks
                        else []
                    )
                    frames.append(
                        ProcessedPoseFrame(
                            frame_index=frame_index,
                            timestamp_ms=timestamp_ms,
                            landmarks=landmarks,
                        )
                    )
                    frame_index += 1
        finally:
            capture.release()

        return FullVideoPoseResult(
            fps=fps,
            total_frames=frame_index,
            processed_frames=frame_index,
            frames=frames,
        )

    @staticmethod
    def _serialize_landmarks(raw_landmarks: list) -> list[PoseLandmark]:
        if len(raw_landmarks) != len(POSE_LANDMARK_NAMES):
            raise PoseExtractionError(
                f"Expected 33 landmarks, received {len(raw_landmarks)}"
            )

        return [
            PoseLandmark(
                index=index,
                name=POSE_LANDMARK_NAMES[index],
                x=float(landmark.x),
                y=float(landmark.y),
                z=float(landmark.z),
                visibility=(
                    float(landmark.visibility)
                    if landmark.visibility is not None
                    else None
                ),
                presence=(
                    float(landmark.presence)
                    if landmark.presence is not None
                    else None
                ),
            )
            for index, landmark in enumerate(raw_landmarks)
        ]
