import {
  ACCEPTED_VIDEO_TYPES,
  MAX_VIDEO_SIZE_BYTES,
} from "@/constants/upload";
import type { FileValidationResult } from "@/types/upload";

export function validateVideoFile(file: File): FileValidationResult {
  if (!ACCEPTED_VIDEO_TYPES.includes(file.type as (typeof ACCEPTED_VIDEO_TYPES)[number])) {
    return { valid: false, message: "Choose an MP4, MOV, or WebM video." };
  }

  if (file.size > MAX_VIDEO_SIZE_BYTES) {
    return { valid: false, message: "Video size must not exceed 200 MB." };
  }

  if (file.size === 0) {
    return { valid: false, message: "The selected video is empty." };
  }

  return { valid: true };
}
