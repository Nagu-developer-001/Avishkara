"use client";

import { useEffect, useState } from "react";

import { BackendStatus } from "@/components/dashboard/backend-status";
import { getBackendHealth } from "@/services/health";
import type { BackendStatus as BackendStatusData } from "@/types/health";

export function BackendHealthCheck() {
  const [status, setStatus] = useState<BackendStatusData | null>(null);

  useEffect(() => {
    let active = true;

    getBackendHealth()
      .then((health) => {
        if (active) setStatus({ available: true, health });
      })
      .catch(() => {
        if (active) setStatus({ available: false });
      });

    return () => {
      active = false;
    };
  }, []);

  return <BackendStatus status={status} />;
}
