"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { RouteLoadingSkeleton } from "@/components/loading/page-skeletons";
import { useAuth } from "@/hooks/use-auth";
import { getCurrentSession } from "@/services/auth";

export function AthleteRoute({ children }: Readonly<{ children: ReactNode }>) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [resolved, setResolved] = useState(false);

  useEffect(() => {
    if (isLoading || !isAuthenticated) return;
    getCurrentSession()
      .then((session) => {
        if (session.role === "authority") router.replace("/authority");
        else setResolved(true);
      })
      .catch(() => router.replace("/login"));
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || (isAuthenticated && !resolved)) {
    return <RouteLoadingSkeleton label="Selecting athlete workspace" />;
  }

  return children;
}
