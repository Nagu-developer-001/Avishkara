"use client";

import { createContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { getCurrentSession, loginUser, registerUser } from "@/services/auth";
import {
  hasValidAccessToken,
  removeAccessToken,
  storeAccessToken,
} from "@/services/token-storage";
import type {
  AuthContextValue,
  LoginPayload,
  RegisterPayload,
  UserRole,
} from "@/types/auth";

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: Readonly<{ children: ReactNode }>) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const validToken = hasValidAccessToken();
    if (!validToken) removeAccessToken();
    setIsAuthenticated(validToken);
    setIsLoading(false);
  }, []);

  async function login(payload: LoginPayload, intendedRole: UserRole) {
    const response = await loginUser(payload);
    storeAccessToken(response.access_token);
    try {
      const session = await getCurrentSession();
      if (session.role !== intendedRole) {
        throw new Error(
          intendedRole === "authority"
            ? "This account does not have Authority access."
            : "Authority login is temporarily disabled for this demo.",
        );
      }
      setIsAuthenticated(true);
      router.replace(session.role === "authority" ? "/authority" : "/dashboard");
    } catch (error) {
      removeAccessToken();
      setIsAuthenticated(false);
      throw error;
    }
  }

  async function register(payload: RegisterPayload) {
    const response = await registerUser(payload);
    storeAccessToken(response.access_token);
    setIsAuthenticated(true);
    router.replace("/dashboard");
  }

  function logout() {
    removeAccessToken();
    setIsAuthenticated(false);
    router.replace("/login");
  }

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
