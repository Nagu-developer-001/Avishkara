"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { RouteLoadingSkeleton } from "@/components/loading/page-skeletons";
import { useAuth } from "@/hooks/use-auth";
import { getCurrentSession } from "@/services/auth";

export function AuthorityRoute({ children }: Readonly<{ children: ReactNode }>) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [authorized, setAuthorized] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    getCurrentSession()
      .then((session) => {
        if (session.role === "authority") setAuthorized(true);
        else router.replace("/dashboard");
      })
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || checking) {
    return <RouteLoadingSkeleton label="Verifying authority access" />;
  }

  if (!authorized) return null;
  return children;
}
