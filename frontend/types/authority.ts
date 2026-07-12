import type { BenchmarkScores, Recommendations } from "@/types/assessment";

export type AuthorityFilters = {
  sport?: string;
  state?: string;
  min_age?: number;
  max_age?: number;
  min_score?: number;
  max_score?: number;
  shortlisted?: boolean;
};

export type AuthorityAthlete = {
  athlete_id: string;
  assessment_id: string;
  name: string;
  sport: string;
  state: string;
  age: number;
  latest_score: number;
  completed_at: string;
  shortlisted: boolean;
};

export type AuthorityDashboard = {
  summary: {
    total_athletes: number;
    total_assessments: number;
    average_overall_score: number | null;
  };
  recent_assessments: Array<{
    assessment_id: string;
    athlete_id: string;
    athlete_name: string;
    sport: string;
    completed_at: string;
    overall_score: number;
  }>;
  athletes: AuthorityAthlete[];
};

export type AuthorityAssessment = {
  assessment_id: string;
  athlete: {
    athlete_id: string;
    name: string;
    age: number;
    gender: string;
    state: string;
    sport: string;
    experience: number;
  };
  video: {
    upload_id: string;
    filename: string;
    sport: string;
    upload_time: string;
    annotated_available: boolean;
  };
  scores: BenchmarkScores;
  recommendations: Recommendations;
  shortlist: {
    shortlisted: boolean;
    shortlisted_at: string | null;
    remarks: string | null;
  };
};

export type ShortlistResponse = {
  athlete_id: string;
  assessment_id: string;
  shortlisted_at: string;
  remarks: string | null;
};
