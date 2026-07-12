export type UploadStatus = "idle" | "ready" | "uploading" | "complete" | "analyzing";

export type Sport = "Running" | "Jumping" | "Bowling";

export type VideoUploadResponse = {
  upload_id: string;
  status: "Uploaded";
};

export type FileValidationResult =
  | { valid: true }
  | { valid: false; message: string };
