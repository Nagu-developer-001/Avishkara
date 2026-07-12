export type MetricDeviation = {
  actual: number;
  target: number;
  signed_deviation: number;
  absolute_deviation: number;
  deviation_percentage: number | null;
  unit: string;
};

export type BilateralMetricDeviation = {
  left: MetricDeviation;
  right: MetricDeviation;
};

export type MetricDeviations = {
  knee_angle: BilateralMetricDeviation;
  elbow_angle: BilateralMetricDeviation;
  hip_angle: BilateralMetricDeviation;
  stride_length: MetricDeviation;
};

export type BenchmarkScores = {
  technique_score: number;
  efficiency_score: number;
  balance_score: number;
  overall_score: number | null;
  metric_deviations: MetricDeviations | null;
  phase_scores: PhaseBenchmarkScore[];
};

export type PhaseBenchmarkScore = {
  movement_phase: string;
  start_frame: number;
  end_frame: number;
  frame_count: number;
  technique_score: number;
  efficiency_score: number;
  balance_score: number;
  overall_score: number;
  metric_deviations: MetricDeviations;
};

export type Recommendations = {
  strengths: string[];
  weaknesses: string[];
  improvement_suggestions: string[];
};

export type AssessmentDetail = {
  video: {
    upload_id: string;
    filename: string;
    sport: string;
    upload_time: string;
    status: string;
    content_type: string;
  };
  scores: BenchmarkScores;
  recommendations: Recommendations;
};

export type AssessmentHistoryItem = {
  upload_id: string;
  filename: string;
  sport: string;
  upload_time: string;
  overall_score: number | null;
};
