from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.constants.pose import POSE_LANDMARK_NAMES
from app.services.mediapipe_pose import MediaPipePoseService, PoseExtractionError


def test_serializes_exactly_33_named_landmarks() -> None:
    raw_landmarks = [
        SimpleNamespace(
            x=index / 100,
            y=index / 100,
            z=0.0,
            visibility=0.95,
            presence=0.98,
        )
        for index in range(33)
    ]

    landmarks = MediaPipePoseService._serialize_landmarks(raw_landmarks)

    assert len(landmarks) == 33
    assert tuple(landmark.name for landmark in landmarks) == POSE_LANDMARK_NAMES
    assert landmarks[0].index == 0
    assert landmarks[32].index == 32
    assert "score" not in landmarks[0].model_dump()


def test_rejects_an_incomplete_landmark_set() -> None:
    with pytest.raises(PoseExtractionError, match="Expected 33"):
        MediaPipePoseService._serialize_landmarks([])


def test_decodes_video_with_real_mediapipe_model(tmp_path: Path) -> None:
    video_path = tmp_path / "blank.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10,
        (96, 96),
    )
    assert writer.isOpened()
    for _ in range(3):
        writer.write(np.zeros((96, 96, 3), dtype=np.uint8))
    writer.release()

    result = MediaPipePoseService().extract(video_path)

    assert result.processed_frames == 3
    assert result.detected_frames == 0
    assert result.frames == []
    assert "score" not in result.model_dump()


def test_full_extraction_preserves_frames_without_detected_pose(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "blank.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10,
        (96, 96),
    )
    assert writer.isOpened()
    for _ in range(2):
        writer.write(np.zeros((96, 96, 3), dtype=np.uint8))
    writer.release()

    result = MediaPipePoseService().extract_all(video_path)

    assert result.total_frames == 2
    assert result.processed_frames == 2
    assert len(result.frames) == 2
    assert all(frame.landmarks == [] for frame in result.frames)
