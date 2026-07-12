import type { BenchmarkScores } from "@/types/assessment";

export type BilateralAngleMetric = {
  left: number;
  right: number;
  unit: "degrees";
};

export type BiomechanicalMetrics = {
  frame_index: number;
  timestamp_ms: number;
  knee_angle: BilateralAngleMetric;
  elbow_angle: BilateralAngleMetric;
  hip_angle: BilateralAngleMetric;
  stride_length: {
    value: number;
    unit: string;
  };
  phases: Array<{
    movement_phase: string;
    start_frame: number;
    end_frame: number;
    frame_count: number;
    knee_angle: BilateralAngleMetric;
    elbow_angle: BilateralAngleMetric;
    hip_angle: BilateralAngleMetric;
    stride_length: {
      value: number;
      unit: string;
    };
  }>;
  running: RunningBiomechanicsMetrics | null;
};

export type RunningGaitEvents = {
  left_foot_strikes: number[];
  left_toe_offs: number[];
  right_foot_strikes: number[];
  right_toe_offs: number[];
};

export type RunningBiomechanicsMetrics = {
  gait_events: RunningGaitEvents;
  stride_analysis: RunningStrideAnalysis;
  step_count: number;
  left_step_count: number;
  right_step_count: number;
  duration_seconds: number | null;
  cadence_spm: number | null;
  mean_stride_time_ms: number | null;
  contact_time_ms: number | null;
  flight_time_ms: number | null;
  duty_factor_pct: number | null;
  stride_length_norm: number | null;
  vertical_oscillation_ratio_pct: number | null;
  overstriding_index_pct: number | null;
  trunk_lean_deg: number | null;
  knee_flex_at_contact_deg: number | null;
  hip_extension_max_deg: number | null;
  ankle_dorsiflexion_contact_deg: number | null;
  pelvic_drop_deg: number | null;
  arm_swing_amplitude_deg: number | null;
  stride_time_symmetry_pct: number | null;
  contact_time_symmetry_pct: number | null;
  knee_angle_symmetry_pct: number | null;
};

export type RunningFootStrike = {
  frame_index: number;
  timestamp_ms: number;
  side: "left" | "right";
  foot_x: number;
  foot_y: number;
  hip_x: number;
  overstride_pct: number | null;
};

export type RunningStrideInterval = {
  side: "left" | "right";
  start_frame: number;
  end_frame: number;
  duration_ms: number;
  stride_length_norm: number | null;
};

export type RunningStepInterval = {
  from_side: "left" | "right";
  to_side: "left" | "right";
  start_frame: number;
  end_frame: number;
  duration_ms: number;
};

export type RunningStrideAnalysis = {
  foot_strikes: RunningFootStrike[];
  stride_intervals: RunningStrideInterval[];
  step_intervals: RunningStepInterval[];
};

export type AnalysisStage =
  | "processing-video"
  | "extracting-pose"
  | "calculating-biomechanics"
  | "comparing-benchmarks"
  | "generating-assessment"
  | "completed";

export type AnalysisStageHandler = (stage: AnalysisStage) => void;

export type { BenchmarkScores };
