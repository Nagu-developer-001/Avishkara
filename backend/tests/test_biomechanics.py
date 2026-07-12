from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import PoseFrame, PoseLandmark
from app.services.biomechanics import BiomechanicsService


def build_pose_frame() -> PoseFrame:
    coordinates = {
        "left_shoulder": (0.20, 0.20),
        "left_elbow": (0.20, 0.30),
        "left_wrist": (0.30, 0.30),
        "left_hip": (0.20, 0.50),
        "left_knee": (0.20, 0.70),
        "left_ankle": (0.40, 0.70),
        "right_shoulder": (0.70, 0.20),
        "right_elbow": (0.70, 0.30),
        "right_wrist": (0.60, 0.30),
        "right_hip": (0.70, 0.50),
        "right_knee": (0.70, 0.70),
        "right_ankle": (0.80, 0.70),
    }
    landmarks = []
    for index, name in enumerate(POSE_LANDMARK_NAMES):
        x, y = coordinates.get(name, (0.50, 0.50))
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
    return PoseFrame(frame_index=8, timestamp_ms=267, landmarks=landmarks)


def test_calculates_joint_angles_and_stride_length() -> None:
    metrics = BiomechanicsService().calculate(build_pose_frame())

    assert metrics.knee_angle.left == 90
    assert metrics.knee_angle.right == 90
    assert metrics.elbow_angle.left == 90
    assert metrics.elbow_angle.right == 90
    assert metrics.hip_angle.left == 180
    assert metrics.hip_angle.right == 180
    assert metrics.stride_length.value == 0.4
    assert metrics.stride_length.unit == "normalized_image_width"


def test_returns_json_without_scoring() -> None:
    result = BiomechanicsService().calculate_json(build_pose_frame())

    assert result["frame_index"] == 8
    assert result["knee_angle"]["unit"] == "degrees"
    assert "score" not in result


def test_accepts_mediapipe_landmarks_outside_image_boundaries() -> None:
    frame = build_pose_frame()
    left_ankle = next(
        landmark for landmark in frame.landmarks if landmark.name == "left_ankle"
    )
    left_ankle.y = 1.167

    metrics = BiomechanicsService().calculate(frame)

    assert 0 <= metrics.knee_angle.left <= 180
