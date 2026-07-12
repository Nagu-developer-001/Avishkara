import { apiClient } from "@/services/api-client";
import type {
  AuthorityAssessment,
  AuthorityDashboard,
  AuthorityFilters,
  ShortlistResponse,
} from "@/types/authority";

export async function getAuthorityDashboard(filters: AuthorityFilters = {}) {
  const response = await apiClient.get<AuthorityDashboard>(
    "/api/v1/authority/dashboard",
    { params: filters },
  );
  return response.data;
}

export async function getAuthorityAssessment(assessmentId: string) {
  const response = await apiClient.get<AuthorityAssessment>(
    `/api/v1/authority/assessments/${assessmentId}`,
  );
  return response.data;
}

async function getVideoBlob(path: string) {
  const response = await apiClient.get<Blob>(path, {
    responseType: "blob",
    timeout: 0,
  });
  return response.data;
}

export function getAuthorityVideo(assessmentId: string) {
  return getVideoBlob(`/api/v1/authority/assessments/${assessmentId}/video`);
}

export function getAuthorityAnnotatedVideo(assessmentId: string) {
  return getVideoBlob(
    `/api/v1/authority/assessments/${assessmentId}/annotated-video`,
  );
}

export async function shortlistAthlete(assessmentId: string, remarks: string) {
  const response = await apiClient.post<ShortlistResponse>(
    `/api/v1/authority/assessments/${assessmentId}/shortlist`,
    { remarks: remarks || null },
  );
  return response.data;
}

export async function getAuthorityAssessmentReport(assessmentId: string) {
  const response = await apiClient.get<Blob>(
    `/api/v1/authority/assessments/${assessmentId}/report`,
    { responseType: "blob", timeout: 0 },
  );
  const disposition = response.headers["content-disposition"] as string | undefined;
  const filename = disposition?.match(/filename="([^"]+)"/)?.[1]
    ?? "avishkara-assessment.pdf";
  return { blob: response.data, filename };
}
