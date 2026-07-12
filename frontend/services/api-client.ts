import axios from "axios";

import { getAccessToken } from "@/services/token-storage";

const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!configuredApiBaseUrl) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
}

export const apiClient = axios.create({
  baseURL: configuredApiBaseUrl.replace(/\/$/, ""),
  timeout: 3000,
  headers: {
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
