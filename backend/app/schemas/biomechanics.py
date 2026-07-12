from pydantic import BaseModel, Field


class BilateralAngleMetric(BaseModel):
    left: float
    right: float
    unit: str = "degrees"


class DistanceMetric(BaseModel):
    value: float = Field(ge=0)
    unit: str


class BiomechanicalMetricValues(BaseModel):
    knee_angle: BilateralAngleMetric
    elbow_angle: BilateralAngleMetric
    hip_angle: BilateralAngleMetric
    stride_length: DistanceMetric


class PhaseBiomechanicalMetrics(BiomechanicalMetricValues):
    movement_phase: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    frame_count: int = Field(gt=0)


class RunningGaitEvents(BaseModel):
    left_foot_strikes: list[int] = Field(default_factory=list)
    left_toe_offs: list[int] = Field(default_factory=list)
    right_foot_strikes: list[int] = Field(default_factory=list)
    right_toe_offs: list[int] = Field(default_factory=list)


class RunningFootStrike(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    side: str
    foot_x: float
    foot_y: float
    hip_x: float
    overstride_pct: float | None = None


class RunningStrideInterval(BaseModel):
    side: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    stride_length_norm: float | None = Field(default=None, ge=0)


class RunningStepInterval(BaseModel):
    from_side: str
    to_side: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    duration_ms: float = Field(ge=0)


class RunningStrideAnalysis(BaseModel):
    foot_strikes: list[RunningFootStrike] = Field(default_factory=list)
    stride_intervals: list[RunningStrideInterval] = Field(default_factory=list)
    step_intervals: list[RunningStepInterval] = Field(default_factory=list)


class RunningBiomechanicsMetrics(BaseModel):
    gait_events: RunningGaitEvents = Field(default_factory=RunningGaitEvents)
    stride_analysis: RunningStrideAnalysis = Field(default_factory=RunningStrideAnalysis)
    step_count: int = Field(default=0, ge=0)
    left_step_count: int = Field(default=0, ge=0)
    right_step_count: int = Field(default=0, ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    cadence_spm: float | None = Field(default=None, ge=0)
    mean_stride_time_ms: float | None = Field(default=None, ge=0)
    contact_time_ms: float | None = Field(default=None, ge=0)
    flight_time_ms: float | None = Field(default=None, ge=0)
    duty_factor_pct: float | None = Field(default=None, ge=0)
    stride_length_norm: float | None = Field(default=None, ge=0)
    vertical_oscillation_ratio_pct: float | None = Field(default=None, ge=0)
    overstriding_index_pct: float | None = None
    trunk_lean_deg: float | None = None
    knee_flex_at_contact_deg: float | None = Field(default=None, ge=0, le=180)
    hip_extension_max_deg: float | None = Field(default=None, ge=0, le=180)
    ankle_dorsiflexion_contact_deg: float | None = Field(default=None, ge=0, le=180)
    pelvic_drop_deg: float | None = Field(default=None, ge=0)
    arm_swing_amplitude_deg: float | None = Field(default=None, ge=0)
    stride_time_symmetry_pct: float | None = Field(default=None, ge=0)
    contact_time_symmetry_pct: float | None = Field(default=None, ge=0)
    knee_angle_symmetry_pct: float | None = Field(default=None, ge=0)


class BiomechanicalMetrics(BiomechanicalMetricValues):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    phases: list[PhaseBiomechanicalMetrics] = Field(default_factory=list)
    running: RunningBiomechanicsMetrics | None = None


class CoachReplayFrame(BiomechanicalMetricValues):
    frame_index: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    movement_phase: str


class CoachReplayTimeline(BaseModel):
    upload_id: str
    total_frames: int = Field(ge=0)
    processed_frames: int = Field(ge=0)
    frames: list[CoachReplayFrame] = Field(default_factory=list)
