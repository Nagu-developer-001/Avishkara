from dataclasses import dataclass

import numpy as np

from app.schemas.jump import (
    Finding,
    JumpAnalysisRequest,
    JumpAnalysisResult,
    Metric,
    Point2D,
    PoseFrame,
)
from app.services.geometry import angle_degrees

GRAVITY_M_S2 = 9.80665
REQUIRED_LANDMARKS = {
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
}


class AnalysisError(ValueError):
    pass


@dataclass(frozen=True)
class JumpEvents:
    takeoff_position: int
    landing_position: int
    baseline_ankle_y: float


def _mean_point(frame: PoseFrame, first: str, second: str) -> Point2D:
    a, b = frame.landmarks[first], frame.landmarks[second]
    return Point2D(
        x=(a.x + b.x) / 2,
        y=(a.y + b.y) / 2,
        visibility=min(a.visibility, b.visibility),
    )


def _validate_landmarks(payload: JumpAnalysisRequest) -> float:
    confidence_values: list[float] = []
    for frame in payload.frames:
        missing = REQUIRED_LANDMARKS - frame.landmarks.keys()
        if missing:
            raise AnalysisError(
                f"Frame {frame.frame_index} is missing: {', '.join(sorted(missing))}"
            )
        confidence_values.extend(
            frame.landmarks[name].visibility for name in REQUIRED_LANDMARKS
        )
    confidence = float(np.mean(confidence_values))
    if confidence < 0.55:
        raise AnalysisError("Pose confidence is too low for a reliable assessment")
    return confidence


def _detect_events(frames: list[PoseFrame]) -> JumpEvents:
    ankle_y = np.asarray(
        [
            _mean_point(frame, "left_ankle", "right_ankle").y
            for frame in frames
        ],
        dtype=float,
    )
    sample_count = max(3, len(frames) // 8)
    baseline = float(np.median(np.r_[ankle_y[:sample_count], ankle_y[-sample_count:]]))

    # Image Y grows downwards. During flight both ankles move above their
    # standing-ground baseline. The adaptive threshold tolerates pose jitter.
    noise = float(np.std(np.r_[ankle_y[:sample_count], ankle_y[-sample_count:]]))
    threshold = max(0.012, noise * 3)
    candidate_airborne = ankle_y < baseline - threshold

    # Require three consecutive frames instead of smoothing the signal. A
    # centered moving average changes the apparent boundary and biases flight
    # time, while this removes isolated pose jitter without shifting events.
    airborne = np.zeros_like(candidate_airborne, dtype=bool)
    for index in range(len(candidate_airborne) - 2):
        if bool(np.all(candidate_airborne[index : index + 3])):
            airborne[index : index + 3] = True

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, is_airborne in enumerate(airborne):
        if is_airborne and start is None:
            start = index
        elif not is_airborne and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(frames) - 1))

    valid_runs = [run for run in runs if run[1] - run[0] >= 3]
    if not valid_runs:
        raise AnalysisError("No clear take-off and landing were detected")
    takeoff, landing = max(valid_runs, key=lambda run: run[1] - run[0])
    if takeoff == 0 or landing >= len(frames) - 1:
        raise AnalysisError("Video must show the athlete grounded before and after the jump")
    return JumpEvents(takeoff, landing, baseline)


def _joint_angle(frame: PoseFrame, side: str) -> float:
    return angle_degrees(
        frame.landmarks[f"{side}_hip"],
        frame.landmarks[f"{side}_knee"],
        frame.landmarks[f"{side}_ankle"],
    )


def _clamp_score(value: float) -> float:
    return round(float(np.clip(value, 0, 100)), 1)


def analyze_vertical_jump(payload: JumpAnalysisRequest) -> JumpAnalysisResult:
    pose_confidence = _validate_landmarks(payload)
    events = _detect_events(payload.frames)
    frames = payload.frames
    takeoff = frames[events.takeoff_position]
    landing = frames[events.landing_position]

    flight_time = (landing.frame_index - takeoff.frame_index) / payload.fps
    if not 0.12 <= flight_time <= 1.5:
        raise AnalysisError("Detected flight time is outside a plausible jump range")
    jump_height = GRAVITY_M_S2 * flight_time**2 / 8
    takeoff_velocity = GRAVITY_M_S2 * flight_time / 2

    preparation_start = max(0, events.takeoff_position - max(3, round(payload.fps * 0.5)))
    preparation_frames = frames[preparation_start : events.takeoff_position + 1]
    knee_angles = [
        (_joint_angle(frame, "left") + _joint_angle(frame, "right")) / 2
        for frame in preparation_frames
    ]
    minimum_knee_angle = float(min(knee_angles))

    left_takeoff = _joint_angle(takeoff, "left")
    right_takeoff = _joint_angle(takeoff, "right")
    takeoff_symmetry = abs(left_takeoff - right_takeoff)

    landing_window = frames[
        events.landing_position : min(len(frames), events.landing_position + 5)
    ]
    hip_x = np.asarray(
        [_mean_point(frame, "left_hip", "right_hip").x for frame in landing_window]
    )
    landing_sway = float(np.ptp(hip_x)) if len(hip_x) > 1 else 0

    propulsion_score = _clamp_score(45 + jump_height * 110)
    symmetry_score = _clamp_score(100 - takeoff_symmetry * 4)
    landing_score = _clamp_score(100 - landing_sway * 700)
    coordination_score = _clamp_score(100 - abs(minimum_knee_angle - 95) * 1.1)

    components = {
        "propulsion": propulsion_score,
        "takeoff_symmetry": symmetry_score,
        "landing_stability": landing_score,
        "coordination": coordination_score,
    }
    score = round(
        propulsion_score * 0.35
        + symmetry_score * 0.25
        + landing_score * 0.20
        + coordination_score * 0.20,
        1,
    )

    findings: list[Finding] = []
    if takeoff_symmetry <= 8:
        findings.append(
            Finding(
                category="strength",
                title="Balanced take-off",
                detail="Left and right knee extension were closely synchronized.",
            )
        )
    else:
        findings.append(
            Finding(
                category="improvement",
                title="Uneven take-off",
                detail=(
                    f"Knee extension differed by {takeoff_symmetry:.1f} degrees; "
                    "review the annotated take-off frame."
                ),
            )
        )
    if landing_sway <= 0.025:
        findings.append(
            Finding(
                category="strength",
                title="Stable landing",
                detail="Hip displacement remained controlled immediately after landing.",
            )
        )
    else:
        findings.append(
            Finding(
                category="improvement",
                title="Landing control",
                detail="Lateral hip movement suggests that landing stability can improve.",
            )
        )

    confidence = round(pose_confidence, 3)
    return JumpAnalysisResult(
        takeoff_frame=takeoff.frame_index,
        landing_frame=landing.frame_index,
        metrics={
            "flight_time": Metric(
                value=round(flight_time, 3),
                unit="s",
                confidence=confidence,
                method="frames between detected take-off and landing / FPS",
            ),
            "jump_height": Metric(
                value=round(jump_height, 3),
                unit="m",
                confidence=confidence,
                method="h = g * flight_time^2 / 8",
            ),
            "takeoff_velocity": Metric(
                value=round(takeoff_velocity, 3),
                unit="m/s",
                confidence=confidence,
                method="v = g * flight_time / 2",
            ),
            "minimum_knee_angle": Metric(
                value=round(minimum_knee_angle, 1),
                unit="degrees",
                confidence=confidence,
                method="2D angle between hip, knee, and ankle",
            ),
            "takeoff_asymmetry": Metric(
                value=round(takeoff_symmetry, 1),
                unit="degrees",
                confidence=confidence,
                method="absolute left-right knee-angle difference",
            ),
        },
        biomechanics_score=score,
        score_components=components,
        findings=findings,
        limitations=[
            "Metrics are 2D video estimates, not force-plate measurements.",
            "Flight-time height assumes take-off and landing at similar body configuration.",
            "A fixed side or front camera and the full body in frame are required.",
        ],
    )
