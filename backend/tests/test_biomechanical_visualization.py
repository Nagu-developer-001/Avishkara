from pathlib import Path

import cv2
import numpy as np

from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import FullVideoPoseResult, PoseLandmark, ProcessedPoseFrame
from app.services.biomechanical_visualization import (
    BiomechanicalVisualizationService,
)


def create_source_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240)
    )
    assert writer.isOpened()
    writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
    writer.release()


def pose_result() -> FullVideoPoseResult:
    coordinates = {
        "left_shoulder": (0.35, 0.30),
        "right_shoulder": (0.65, 0.30),
        "left_elbow": (0.28, 0.45),
        "right_elbow": (0.72, 0.45),
        "left_wrist": (0.22, 0.60),
        "right_wrist": (0.78, 0.60),
        "left_hip": (0.42, 0.55),
        "right_hip": (0.58, 0.55),
        "left_knee": (0.40, 0.72),
        "right_knee": (0.60, 0.72),
        "left_ankle": (0.38, 0.90),
        "right_ankle": (0.62, 0.90),
    }
    landmarks = [
        PoseLandmark(
            index=index,
            name=name,
            x=coordinates.get(name, (0.5, 0.2))[0],
            y=coordinates.get(name, (0.5, 0.2))[1],
            z=0,
            visibility=0.99,
            presence=0.99,
        )
        for index, name in enumerate(POSE_LANDMARK_NAMES)
    ]
    return FullVideoPoseResult(
        fps=10,
        total_frames=1,
        processed_frames=1,
        frames=[
            ProcessedPoseFrame(
                frame_index=0,
                timestamp_ms=0,
                landmarks=landmarks,
            )
        ],
    )


def test_generates_a_separate_annotated_video(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    annotated = tmp_path / "annotated" / "preview.mp4"
    create_source_video(source)

    result = BiomechanicalVisualizationService().generate(
        video_path=source,
        pose_result=pose_result(),
        output_path=annotated,
    )

    assert result == annotated
    assert source.is_file()
    assert annotated.is_file()
    assert annotated != source
    capture = cv2.VideoCapture(str(annotated))
    success, frame = capture.read()
    capture.release()
    assert success
    assert np.count_nonzero(frame) > 0
