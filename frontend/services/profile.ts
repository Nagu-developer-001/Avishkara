import { apiClient } from "@/services/api-client";
import type { AthleteProfile } from "@/types/athlete";

export async function getAthleteProfile() {
  const response = await apiClient.get<AthleteProfile>("/profile");
  return response.data;
}

export async function updateAthleteProfile(profile: AthleteProfile) {
  const response = await apiClient.put<AthleteProfile>("/profile", profile);
  return response.data;
}
