import { apiClient } from "@/services/api-client";
import type { Sport, VideoUploadResponse } from "@/types/upload";

export async function uploadVideo(
  file: File,
  sport: Sport,
  onProgress: (progress: number) => void,
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("sport", sport);

  const response = await apiClient.post<VideoUploadResponse>(
    "/api/v1/videos/upload",
    formData,
    {
      timeout: 5 * 60 * 1000,
      onUploadProgress: (event) => {
        if (!event.total) return;
        onProgress(Math.min(100, Math.round((event.loaded * 100) / event.total)));
      },
    },
  );
  return response.data;
}
