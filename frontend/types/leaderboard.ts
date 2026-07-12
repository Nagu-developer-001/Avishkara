export type LeaderboardEntry = {
  rank: number;
  athlete_id: string;
  assessment_id: string;
  upload_id: string;
  name: string;
  sport: string;
  state: string;
  overall_score: number;
  technique_score: number;
  efficiency_score: number;
  balance_score: number;
  completed_at: string;
  is_current_user: boolean;
};

export type LeaderboardResponse = {
  top_athletes: LeaderboardEntry[];
  current_user_entry: LeaderboardEntry | null;
};

export type LeaderboardFilters = {
  sport?: string;
  state?: string;
  gender?: string;
  min_age?: number;
  max_age?: number;
  min_experience?: number;
  max_experience?: number;
};
