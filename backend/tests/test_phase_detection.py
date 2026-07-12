import math

import pytest

from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import PoseFrame, PoseLandmark
from app.services.phase_detection import PhaseDetectionService, SPORT_PHASES


def motion_frames(count: int = 20) -> list[PoseFrame]:
    frames = []
    for frame_index in range(count):
        progress = frame_index / (count - 1)
        jump_arc = 0.15 * math.sin(math.pi * progress)
        coordinates = {
            "left_shoulder": (0.4, 0.25 - jump_arc),
            "right_shoulder": (0.6, 0.25 - jump_arc),
            "left_hip": (0.45, 0.5 - jump_arc),
            "right_hip": (0.55, 0.5 - jump_arc),
            "left_knee": (0.43, 0.7 - jump_arc),
            "right_knee": (0.57, 0.7 - jump_arc),
            "left_ankle": (0.35 + 0.25 * progress, 0.9 - jump_arc / 2),
            "right_ankle": (0.65 - 0.25 * progress, 0.9 - jump_arc / 2),
            "left_wrist": (0.25 + 0.4 * progress, 0.5 - 0.2 * math.sin(2 * math.pi * progress)),
            "right_wrist": (0.75 - 0.1 * progress, 0.5),
        }
        landmarks = []
        for index, name in enumerate(POSE_LANDMARK_NAMES):
            x, y = coordinates.get(name, (0.5, 0.4))
            landmarks.append(
                PoseLandmark(
                    index=index,
                    name=name,
                    x=x,
                    y=y,
                    z=0,
                    visibility=0.99,
                    presence=0.99,
                )
            )
        frames.append(
            PoseFrame(
                frame_index=frame_index,
                timestamp_ms=frame_index * 33,
                landmarks=landmarks,
            )
        )
    return frames


@pytest.mark.parametrize("sport", ["Running", "Jumping", "Bowling"])
def test_detects_all_ordered_phases_with_nonempty_frame_ranges(sport: str) -> None:
    detected = PhaseDetectionService().detect(motion_frames(), sport)

    assert tuple(phase.name for phase in detected) == SPORT_PHASES[sport]
    assert all(phase.frame_indexes for phase in detected)
    assert detected[0].start_frame == 0
    assert detected[-1].end_frame == 19
    assert all(
        current.end_frame < following.start_frame
        for current, following in zip(detected, detected[1:])
    )


def test_detection_is_deterministic() -> None:
    frames = motion_frames()

    first = PhaseDetectionService().detect(frames, "Bowling")
    second = PhaseDetectionService().detect(frames, "Bowling")

    assert first == second
