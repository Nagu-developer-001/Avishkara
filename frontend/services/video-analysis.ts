import { apiClient } from "@/services/api-client";
import type {
  AnalysisStageHandler,
  BenchmarkScores,
  BiomechanicalMetrics,
} from "@/types/analysis";

const ANALYSIS_TIMEOUT_MS = 10 * 60 * 1000;

function nextPaint() {
  return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
}

export async function analyzeVideo(uploadId: string, onStage: AnalysisStageHandler) {
  onStage("processing-video");
  await nextPaint();

  onStage("extracting-pose");
  await apiClient.post(`/api/v1/videos/${uploadId}/process`, undefined, {
    timeout: ANALYSIS_TIMEOUT_MS,
  });

  onStage("calculating-biomechanics");
  const biomechanics = await apiClient.post<BiomechanicalMetrics>(
    `/api/v1/videos/${uploadId}/biomechanics`,
    undefined,
    { timeout: ANALYSIS_TIMEOUT_MS },
  );

  onStage("comparing-benchmarks");
  const benchmark = await apiClient.post<BenchmarkScores>(
    `/api/v1/videos/${uploadId}/benchmark`,
    biomechanics.data,
    { timeout: ANALYSIS_TIMEOUT_MS },
  );

  onStage("generating-assessment");
  await apiClient.post(
    `/api/v1/videos/${uploadId}/assessment`,
    benchmark.data,
    { timeout: ANALYSIS_TIMEOUT_MS },
  );

  onStage("completed");
}

export async function getStoredBiomechanics(uploadId: string) {
  const response = await apiClient.post<BiomechanicalMetrics>(
    `/api/v1/videos/${uploadId}/biomechanics`,
    undefined,
    { timeout: ANALYSIS_TIMEOUT_MS },
  );
  return response.data;
}

export async function getLeaderboardStoredBiomechanics(uploadId: string) {
  const response = await apiClient.get<BiomechanicalMetrics>(
    `/api/v1/videos/leaderboard/${uploadId}/biomechanics`,
    { timeout: ANALYSIS_TIMEOUT_MS },
  );
  return response.data;
}
