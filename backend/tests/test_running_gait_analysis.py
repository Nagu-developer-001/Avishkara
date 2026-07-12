import math

from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import PoseFrame, PoseLandmark
from app.services.running_gait_analysis import RunningGaitAnalysisService


def running_frames(count: int = 90, fps: int = 30) -> list[PoseFrame]:
    frames = []
    for frame_index in range(count):
        time = frame_index / fps
        progress = frame_index / (count - 1)
        hip_x = 0.35 + 0.28 * progress
        hip_y = 0.52 + 0.015 * math.sin(2 * math.pi * frame_index / 30)
        left_cycle = math.cos(2 * math.pi * (frame_index - 8) / 30)
        right_cycle = math.cos(2 * math.pi * (frame_index - 23) / 30)
        left_foot_y = 0.78 + 0.08 * left_cycle
        right_foot_y = 0.78 + 0.08 * right_cycle

        coordinates = {
            "left_shoulder": (hip_x - 0.04, hip_y - 0.26),
            "right_shoulder": (hip_x + 0.04, hip_y - 0.26),
            "left_elbow": (hip_x - 0.10, hip_y - 0.14),
            "right_elbow": (hip_x + 0.10, hip_y - 0.14),
            "left_wrist": (hip_x - 0.12, hip_y - 0.02),
            "right_wrist": (hip_x + 0.12, hip_y - 0.02),
            "left_hip": (hip_x - 0.04, hip_y),
            "right_hip": (hip_x + 0.04, hip_y),
            "left_knee": (hip_x - 0.055, hip_y + 0.14),
            "right_knee": (hip_x + 0.055, hip_y + 0.14),
            "left_ankle": (hip_x - 0.12 + 0.03 * math.sin(time * 4), left_foot_y),
            "right_ankle": (hip_x + 0.12 - 0.03 * math.sin(time * 4), right_foot_y),
            "left_heel": (hip_x - 0.13, left_foot_y + 0.01),
            "right_heel": (hip_x + 0.13, right_foot_y + 0.01),
            "left_foot_index": (hip_x - 0.16, left_foot_y),
            "right_foot_index": (hip_x + 0.16, right_foot_y),
        }

        landmarks = []
        for index, name in enumerate(POSE_LANDMARK_NAMES):
            x, y = coordinates.get(name, (hip_x, hip_y - 0.35))
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
                timestamp_ms=round(frame_index * 1000 / fps),
                landmarks=landmarks,
            )
        )
    return frames


def noisy_running_frames() -> list[PoseFrame]:
    frames = running_frames()
    for frame in frames:
        jitter = 0.012 if frame.frame_index % 4 == 0 else -0.008
        for landmark in frame.landmarks:
            if landmark.name in {"left_ankle", "left_heel", "right_ankle", "right_heel"}:
                landmark.y += jitter
    return frames


def test_detects_running_foot_strikes_and_toe_offs() -> None:
    result = RunningGaitAnalysisService().analyze(running_frames())

    assert result.left_step_count >= 2
    assert result.right_step_count >= 2
    assert result.step_count == result.left_step_count + result.right_step_count
    assert result.gait_events.left_foot_strikes == sorted(result.gait_events.left_foot_strikes)
    assert result.gait_events.right_foot_strikes == sorted(result.gait_events.right_foot_strikes)
    assert all(
        strike < toe_off
        for strike, toe_off in zip(
            result.gait_events.left_foot_strikes,
            result.gait_events.left_toe_offs,
        )
    )


def test_calculates_basic_running_timing_metrics() -> None:
    result = RunningGaitAnalysisService().analyze(running_frames())

    assert result.duration_seconds == 2.967
    assert result.cadence_spm is not None
    assert result.cadence_spm > 0
    assert result.mean_stride_time_ms is not None
    assert result.contact_time_ms is not None
    assert result.duty_factor_pct is not None
    assert result.stride_length_norm is not None
    assert result.vertical_oscillation_ratio_pct is not None
    assert result.overstriding_index_pct is not None


def test_calculates_stride_sequence_for_visual_analysis() -> None:
    result = RunningGaitAnalysisService().analyze(running_frames())

    strikes = result.stride_analysis.foot_strikes
    assert len(strikes) == result.step_count
    assert [strike.frame_index for strike in strikes] == sorted(
        strike.frame_index for strike in strikes
    )
    assert {strike.side for strike in strikes} == {"left", "right"}
    assert all(
        current.side != following.side
        for current, following in zip(strikes, strikes[1:])
    )
    assert all(0 <= strike.foot_x <= 1 for strike in strikes)
    assert all(0 <= strike.foot_y <= 1 for strike in strikes)

    assert result.stride_analysis.stride_intervals
    assert all(
        interval.end_frame > interval.start_frame
        for interval in result.stride_analysis.stride_intervals
    )
    assert all(
        interval.duration_ms > 0
        for interval in result.stride_analysis.stride_intervals
    )
    assert result.stride_analysis.step_intervals


def test_noisy_foot_motion_does_not_create_duplicate_stride_contacts() -> None:
    result = RunningGaitAnalysisService().analyze(noisy_running_frames())
    strikes = result.stride_analysis.foot_strikes

    assert len(strikes) <= 7
    assert all(
        current.side != following.side
        for current, following in zip(strikes, strikes[1:])
    )
    assert all(
        following.frame_index - current.frame_index >= 5
        for current, following in zip(strikes, strikes[1:])
    )


def test_returns_empty_running_metrics_for_short_clips() -> None:
    result = RunningGaitAnalysisService().analyze(running_frames(count=2))

    assert result.step_count == 0
    assert result.cadence_spm is None
    assert result.gait_events.left_foot_strikes == []
    assert result.stride_analysis.foot_strikes == []
