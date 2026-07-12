import type { ReactNode } from "react";

import { AthleteShell } from "@/components/dashboard/athlete-shell";

export default function DashboardLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <AthleteShell>{children}</AthleteShell>;
}
