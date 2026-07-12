import { apiClient } from "@/services/api-client";
import type {
  AuthResponse,
  LoginPayload,
  RegisterPayload,
  SessionResponse,
} from "@/types/auth";

export async function loginUser(payload: LoginPayload) {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/login", payload);
  return response.data;
}

export async function registerUser(payload: RegisterPayload) {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/register", payload);
  return response.data;
}

export async function getCurrentSession() {
  const response = await apiClient.get<SessionResponse>("/api/v1/auth/me");
  return response.data;
}
