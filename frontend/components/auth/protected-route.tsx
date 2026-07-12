"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { RouteLoadingSkeleton } from "@/components/loading/page-skeletons";
import { useAuth } from "@/hooks/use-auth";

export function ProtectedRoute({ children }: Readonly<{ children: ReactNode }>) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <RouteLoadingSkeleton label="Checking session" />;
  }
  if (!isAuthenticated) return null;
  return children;
}
