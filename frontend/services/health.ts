import { apiClient } from "@/services/api-client";
import type { BackendHealth } from "@/types/health";

export async function getBackendHealth() {
  const response = await apiClient.get<BackendHealth>("/health");
  return response.data;
}
