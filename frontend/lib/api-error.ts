import axios from "axios";

type FastApiError = {
  detail?: string | Array<{ msg?: string }>;
};

export function getApiErrorMessage(error: unknown) {
  if (!axios.isAxiosError<FastApiError>(error)) {
    if (error instanceof Error) return error.message;
    return "Something went wrong. Please try again.";
  }

  if (error.code === "ECONNABORTED") {
    return "The analysis took too long. Please try again.";
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (!error.response) {
    return "The backend connection was interrupted. Please try again.";
  }
  return "Request failed. Please check your details.";
}

export function isApiErrorStatus(error: unknown, status: number) {
  return axios.isAxiosError(error) && error.response?.status === status;
}
