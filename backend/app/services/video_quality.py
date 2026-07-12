import math

from app.schemas.pose import FullVideoPoseResult, ProcessedPoseFrame
from app.schemas.video_quality import VideoQualityResult

MIN_DETECTED_FRAMES = 5
MIN_FULL_BODY_FRAME_RATIO = 0.6
MIN_LANDMARK_VISIBILITY = 0.5
FULL_BODY_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


class VideoQualityError(ValueError):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__(" ".join(reasons))


class VideoQualityService:
    def validate(
        self, pose_result: FullVideoPoseResult, sport: str
    ) -> VideoQualityResult:
        detected = [frame for frame in pose_result.frames if frame.landmarks]
        full_body = [frame for frame in detected if self._has_full_body(frame)]
        reasons: list[str] = []

        if len(detected) < MIN_DETECTED_FRAMES:
            reasons.append(
                "The video does not contain enough reliably detected pose frames."
            )
        full_body_ratio = len(full_body) / len(detected) if detected else 0
        if full_body_ratio < MIN_FULL_BODY_FRAME_RATIO:
            reasons.append(
                "Keep the athlete's complete body visible, including shoulders, hips, knees, and ankles."
            )
        if not reasons and not self._has_sport_movement(full_body, sport):
            reasons.append(
                f"The video does not contain enough visible {sport.lower()} movement for analysis."
            )
        if not reasons and sport == "Running" and not self._has_running_side_view(full_body):
            reasons.append(
                "Running stride analysis needs a clear side-view video. Record the athlete from the side with full body visible."
            )

        return VideoQualityResult(
            valid=not reasons,
            reasons=reasons,
            detected_frames=len(detected),
            full_body_frames=len(full_body),
        )

    @staticmethod
    def _has_full_body(frame: ProcessedPoseFrame) -> bool:
        landmarks = {landmark.name: landmark for landmark in frame.landmarks}
        return all(
            name in landmarks
            and (landmarks[name].visibility or 0) >= MIN_LANDMARK_VISIBILITY
            and 0 <= landmarks[name].x <= 1
            and 0 <= landmarks[name].y <= 1
            for name in FULL_BODY_LANDMARKS
        )

    def _has_sport_movement(
        self, frames: list[ProcessedPoseFrame], sport: str
    ) -> bool:
        if sport == "Running":
            return self._maximum_travel(frames, ("left_ankle", "right_ankle")) >= 0.08
        if sport == "Jumping":
            return self._vertical_center_range(
                frames, "left_hip", "right_hip"
            ) >= 0.05
        if sport == "Bowling":
            wrist_travel = self._maximum_travel(
                frames, ("left_wrist", "right_wrist")
            )
            ankle_travel = self._maximum_travel(
                frames, ("left_ankle", "right_ankle")
            )
            return (
                wrist_travel >= 0.12
                and ankle_travel >= 0.05
                and self._has_overhead_bowling_arm(frames)
            )
        return False

    @staticmethod
    def _has_running_side_view(frames: list[ProcessedPoseFrame]) -> bool:
        relative_ranges = []
        for side in ("left", "right"):
            values = []
            for frame in frames:
                landmarks = {landmark.name: landmark for landmark in frame.landmarks}
                ankle = landmarks.get(f"{side}_ankle")
                hip = landmarks.get(f"{side}_hip")
                if ankle is not None and hip is not None:
                    values.append(ankle.x - hip.x)
            if values:
                relative_ranges.append(max(values) - min(values))
        return max(relative_ranges, default=0) >= 0.06

    def _has_overhead_bowling_arm(
        self, frames: list[ProcessedPoseFrame]
    ) -> bool:
        required_events = max(1, round(len(frames) * 0.02))
        events = 0
        for frame in frames:
            landmarks = {landmark.name: landmark for landmark in frame.landmarks}
            for side in ("left", "right"):
                shoulder = landmarks[f"{side}_shoulder"]
                elbow = landmarks[f"{side}_elbow"]
                wrist = landmarks[f"{side}_wrist"]
                if (
                    wrist.y < shoulder.y - 0.02
                    and elbow.y < shoulder.y + 0.08
                    and self._angle(shoulder, elbow, wrist) >= 120
                ):
                    events += 1
                    break
        return events >= required_events

    @staticmethod
    def _angle(first, vertex, third) -> float:
        first_vector = (first.x - vertex.x, first.y - vertex.y)
        second_vector = (third.x - vertex.x, third.y - vertex.y)
        denominator = math.hypot(*first_vector) * math.hypot(*second_vector)
        if denominator == 0:
            return 0
        cosine = sum(
            left * right
            for left, right in zip(first_vector, second_vector, strict=True)
        ) / denominator
        return math.degrees(math.acos(max(-1, min(1, cosine))))

    @staticmethod
    def _maximum_travel(
        frames: list[ProcessedPoseFrame], names: tuple[str, ...]
    ) -> float:
        coordinates: dict[str, list[tuple[float, float]]] = {
            name: [] for name in names
        }
        for frame in frames:
            landmarks = {landmark.name: landmark for landmark in frame.landmarks}
            for name in names:
                if name in landmarks:
                    coordinates[name].append(
                        (landmarks[name].x, landmarks[name].y)
                    )
        ranges = []
        for points in coordinates.values():
            if not points:
                continue
            x_range = max(point[0] for point in points) - min(
                point[0] for point in points
            )
            y_range = max(point[1] for point in points) - min(
                point[1] for point in points
            )
            ranges.append(math.hypot(x_range, y_range))
        return max(ranges, default=0)

    @staticmethod
    def _vertical_center_range(
        frames: list[ProcessedPoseFrame], left_name: str, right_name: str
    ) -> float:
        centers = []
        for frame in frames:
            landmarks = {landmark.name: landmark for landmark in frame.landmarks}
            if left_name in landmarks and right_name in landmarks:
                centers.append(
                    (landmarks[left_name].y + landmarks[right_name].y) / 2
                )
        return max(centers) - min(centers) if centers else 0
