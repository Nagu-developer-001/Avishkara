import { apiClient } from "@/services/api-client";
import type { LeaderboardFilters, LeaderboardResponse } from "@/types/leaderboard";

export async function getLeaderboard(filters: LeaderboardFilters = {}) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== ""),
  );
  const response = await apiClient.get<LeaderboardResponse>("/api/v1/videos/leaderboard", {
    params,
  });
  return response.data;
}
