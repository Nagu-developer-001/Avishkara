from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import (
    FullVideoPoseResult,
    PoseLandmark,
    ProcessedPoseFrame,
)
from app.services.video_quality import VideoQualityService


def pose_result(
    *,
    sport: str,
    cropped: bool = False,
    moving: bool = True,
    overhead: bool | None = None,
    front_view_running: bool = False,
) -> tuple[FullVideoPoseResult, str]:
    overhead = sport == "Bowling" and moving if overhead is None else overhead
    frames = []
    for frame_index in range(6):
        coordinates = {
            "left_shoulder": (0.4, 0.2),
            "right_shoulder": (0.6, 0.2),
            "left_hip": (0.45, 0.5),
            "right_hip": (0.55, 0.5),
            "left_knee": (0.45, 0.7),
            "right_knee": (0.55, 0.7),
            "left_ankle": (0.4 + (0.02 * frame_index if moving else 0), 0.9),
            "right_ankle": (0.6 - (0.02 * frame_index if moving else 0), 0.9),
            "left_wrist": (0.3 + (0.03 * frame_index if moving else 0), 0.45),
            "right_wrist": (0.7 - (0.03 * frame_index if moving else 0), 0.45),
            "left_elbow": (0.35, 0.35),
            "right_elbow": (0.65, 0.35),
        }
        if overhead and frame_index >= 4:
            coordinates["left_elbow"] = (0.38, 0.12)
            coordinates["left_wrist"] = (0.36, 0.02)
        if sport == "Jumping" and moving:
            coordinates["left_hip"] = (0.45, 0.5 - 0.012 * frame_index)
            coordinates["right_hip"] = (0.55, 0.5 - 0.012 * frame_index)
        if front_view_running:
            coordinates["left_ankle"] = (0.42, 0.9 - 0.02 * frame_index)
            coordinates["right_ankle"] = (0.58, 0.9 + 0.02 * frame_index)
        if cropped:
            for name in (
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ):
                coordinates[name] = (coordinates[name][0], 1.5)

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
            ProcessedPoseFrame(
                frame_index=frame_index,
                timestamp_ms=frame_index * 33,
                landmarks=landmarks,
            )
        )
    return (
        FullVideoPoseResult(
            fps=30,
            total_frames=len(frames),
            processed_frames=len(frames),
            frames=frames,
        ),
        sport,
    )


def test_rejects_a_cropped_body() -> None:
    result, sport = pose_result(sport="Bowling", cropped=True)

    quality = VideoQualityService().validate(result, sport)

    assert quality.valid is False
    assert quality.full_body_frames == 0
    assert "complete body" in quality.reasons[0]


def test_rejects_a_stationary_clip() -> None:
    result, sport = pose_result(sport="Bowling", moving=False)

    quality = VideoQualityService().validate(result, sport)

    assert quality.valid is False
    assert "bowling movement" in quality.reasons[0]


def test_rejects_running_arm_swing_when_bowling_is_selected() -> None:
    result, sport = pose_result(sport="Bowling", moving=True, overhead=False)

    quality = VideoQualityService().validate(result, sport)

    assert quality.valid is False
    assert "bowling movement" in quality.reasons[0]


def test_rejects_wrong_camera_angle_for_running_stride_analysis() -> None:
    result, sport = pose_result(sport="Running", front_view_running=True)

    quality = VideoQualityService().validate(result, sport)

    assert quality.valid is False
    assert "side-view" in quality.reasons[0]


def test_accepts_visible_movement_for_each_supported_sport() -> None:
    for sport in ("Running", "Jumping", "Bowling"):
        result, _ = pose_result(sport=sport)

        quality = VideoQualityService().validate(result, sport)

        assert quality.valid is True, (sport, quality.reasons)
