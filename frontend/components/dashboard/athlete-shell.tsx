import type { ReactNode } from "react";

import { AthleteRoute } from "@/components/auth/athlete-route";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { PageTransition } from "@/components/motion/page-transition";
import { Sidebar } from "@/components/dashboard/sidebar";

export function AthleteShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <ProtectedRoute>
      <AthleteRoute>
        <div className="relative min-h-screen overflow-x-hidden bg-background">
          <div className="sport-grid pointer-events-none fixed inset-0 opacity-40" />
          <Sidebar />
          <main className="relative min-w-0 px-4 pb-32 pt-24 sm:px-8 lg:ml-72 lg:px-10 lg:py-10 xl:px-14">
            <div className="mx-auto w-full max-w-[1480px]">
              <PageTransition>{children}</PageTransition>
            </div>
          </main>
        </div>
      </AthleteRoute>
    </ProtectedRoute>
  );
}
