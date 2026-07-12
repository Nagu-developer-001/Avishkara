from dataclasses import dataclass

from app.schemas.biomechanics import (
    BilateralAngleMetric,
    BiomechanicalMetrics,
    DistanceMetric,
)
from app.schemas.pose import PoseFrame, PoseLandmark
from app.services.geometry import angle_degrees


@dataclass(frozen=True)
class LandmarkPoint:
    x: float
    y: float


class BiomechanicsService:
    def calculate(self, frame: PoseFrame) -> BiomechanicalMetrics:
        landmarks = {landmark.name: landmark for landmark in frame.landmarks}

        knee_angle = self._bilateral_angle(
            landmarks,
            first="hip",
            vertex="knee",
            third="ankle",
        )
        elbow_angle = self._bilateral_angle(
            landmarks,
            first="shoulder",
            vertex="elbow",
            third="wrist",
        )
        hip_angle = self._bilateral_angle(
            landmarks,
            first="shoulder",
            vertex="hip",
            third="knee",
        )
        stride_length = abs(
            landmarks["left_ankle"].x - landmarks["right_ankle"].x
        )

        return BiomechanicalMetrics(
            frame_index=frame.frame_index,
            timestamp_ms=frame.timestamp_ms,
            knee_angle=knee_angle,
            elbow_angle=elbow_angle,
            hip_angle=hip_angle,
            stride_length=DistanceMetric(
                value=round(stride_length, 4),
                unit="normalized_image_width",
            ),
        )

    def calculate_json(self, frame: PoseFrame) -> dict:
        return self.calculate(frame).model_dump(mode="json")

    @staticmethod
    def _bilateral_angle(
        landmarks: dict[str, PoseLandmark],
        *,
        first: str,
        vertex: str,
        third: str,
    ) -> BilateralAngleMetric:
        angles: dict[str, float] = {}
        for side in ("left", "right"):
            angles[side] = round(
                angle_degrees(
                    BiomechanicsService._point(landmarks[f"{side}_{first}"]),
                    BiomechanicsService._point(landmarks[f"{side}_{vertex}"]),
                    BiomechanicsService._point(landmarks[f"{side}_{third}"]),
                ),
                2,
            )
        return BilateralAngleMetric(left=angles["left"], right=angles["right"])

    @staticmethod
    def _point(landmark: PoseLandmark) -> LandmarkPoint:
        return LandmarkPoint(
            x=landmark.x,
            y=landmark.y,
        )
from dataclasses import dataclass
