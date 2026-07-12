export type ProgressTrendPoint = {
  upload_id: string;
  sport: string;
  upload_time: string;
  overall_score: number;
  technique_score: number;
  efficiency_score: number;
  balance_score: number;
};

export type AthleteProgressAnalytics = {
  assessment_count: number;
  average_score: number | null;
  best_score: number | null;
  improvement: number | null;
  trend: ProgressTrendPoint[];
};
