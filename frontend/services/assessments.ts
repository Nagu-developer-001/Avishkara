import { apiClient } from "@/services/api-client";
import { getAccessToken } from "@/services/token-storage";
import type { AssessmentDetail, AssessmentHistoryItem } from "@/types/assessment";
import type { AthleteProgressAnalytics } from "@/types/progress";

const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function apiBaseUrl() {
  if (!configuredApiBaseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
  return configuredApiBaseUrl.replace(/\/$/, "");
}

function mediaUrl(path: string) {
  const token = getAccessToken();
  const url = new URL(`${apiBaseUrl()}${path}`);
  if (token) url.searchParams.set("media_token", token);
  return url.toString();
}

export async function getAssessment(uploadId: string) {
  const response = await apiClient.get<AssessmentDetail>(
    `/api/v1/videos/${uploadId}/results`,
  );
  return response.data;
}

export async function getLeaderboardAssessment(uploadId: string) {
  const response = await apiClient.get<AssessmentDetail>(
    `/api/v1/videos/leaderboard/${uploadId}/results`,
  );
  return response.data;
}

export async function getAssessmentHistory() {
  const response = await apiClient.get<AssessmentHistoryItem[]>("/api/v1/videos/history");
  return response.data;
}

export async function getAthleteProgress() {
  const response = await apiClient.get<AthleteProgressAnalytics>(
    "/api/v1/videos/analytics/progress",
  );
  return response.data;
}

export async function getUploadedVideo(uploadId: string) {
  const response = await apiClient.get<Blob>(`/api/v1/videos/${uploadId}/content`, {
    responseType: "blob",
    timeout: 0,
  });
  return response.data;
}

export async function getAnnotatedVideo(uploadId: string) {
  const response = await apiClient.get<Blob>(
    `/api/v1/videos/${uploadId}/annotated-content`,
    {
      responseType: "blob",
      timeout: 0,
    },
  );
  return response.data;
}

export function getUploadedVideoUrl(uploadId: string) {
  return mediaUrl(`/api/v1/videos/${uploadId}/content`);
}

export function getAnnotatedVideoUrl(uploadId: string) {
  return mediaUrl(`/api/v1/videos/${uploadId}/annotated-content`);
}

export function getLeaderboardUploadedVideoUrl(uploadId: string) {
  return mediaUrl(`/api/v1/videos/leaderboard/${uploadId}/content`);
}

export function getLeaderboardAnnotatedVideoUrl(uploadId: string) {
  return mediaUrl(`/api/v1/videos/leaderboard/${uploadId}/annotated-content`);
}

export async function getAssessmentReport(uploadId: string) {
  const response = await apiClient.get<Blob>(
    `/api/v1/videos/${uploadId}/report`,
    { responseType: "blob", timeout: 0 },
  );
  const disposition = response.headers["content-disposition"] as string | undefined;
  const filename = disposition?.match(/filename="([^"]+)"/)?.[1]
    ?? "avishkara-assessment.pdf";
  return { blob: response.data, filename };
}

export async function getLeaderboardAssessmentReport(uploadId: string) {
  const response = await apiClient.get<Blob>(
    `/api/v1/videos/leaderboard/${uploadId}/report`,
    { responseType: "blob", timeout: 0 },
  );
  const disposition = response.headers["content-disposition"] as string | undefined;
  const filename = disposition?.match(/filename="([^"]+)"/)?.[1]
    ?? "avishkara-assessment.pdf";
  return { blob: response.data, filename };
}
