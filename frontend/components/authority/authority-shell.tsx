"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { AppLogo } from "@/components/brand/app-logo";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { useAuth } from "@/hooks/use-auth";
import { PageTransition } from "@/components/motion/page-transition";

export function AuthorityShell({ children }: Readonly<{ children: ReactNode }>) {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <header className="navigation-surface mobile-safe-top sticky top-0 z-50 border-b backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-[1540px] items-center justify-between gap-3 px-4 py-2 sm:h-20 sm:px-8 sm:py-0">
          <Link href="/authority" className="flex min-w-0 items-center gap-3">
            <AppLogo authority imageClassName="object-cover" size="compact" />
          </Link>
          <div className="flex shrink-0 items-center gap-1 sm:gap-2"><ThemeSwitcher compact /><Button type="button" variant="ghost" size="sm" onClick={logout}><span className="hidden sm:inline">Sign out</span><span className="sm:hidden">Exit</span></Button></div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1540px] px-4 pb-10 pt-7 sm:px-8 sm:py-10"><PageTransition>{children}</PageTransition></main>
    </div>
  );
}
