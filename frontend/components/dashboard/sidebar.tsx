"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { AppLogo } from "@/components/brand/app-logo";
import { DASHBOARD_NAVIGATION } from "@/constants/navigation";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { SportIcon, type SportIconName } from "@/components/ui/sport-icon";
import { LineSidebar } from "@/components/ui/line-sidebar";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";

export function Sidebar() {
  const { logout } = useAuth();
  const pathname = usePathname();

  const activeIndex = DASHBOARD_NAVIGATION.findIndex((item) =>
    item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href),
  );

  const desktopNavigation = (
    <LineSidebar
      ariaLabel="Dashboard navigation"
      activeIndex={Math.max(activeIndex, 0)}
      className="flex flex-1"
      fontSize={0.95}
      itemGap={18}
      markerLength={74}
      maxShift={42}
      proximityRadius={140}
      showIndex={false}
      smoothing={100}
      items={DASHBOARD_NAVIGATION.map((item) => ({
        href: item.href,
        label: item.label,
      }))}
    />
  );

  return (
    <>
      <aside className="navigation-surface fixed inset-y-0 left-0 z-40 hidden h-dvh w-72 flex-col overflow-y-auto overscroll-contain border-r p-5 backdrop-blur-2xl lg:flex">
        <Link href="/dashboard" className="flex items-center gap-3 px-2 py-3">
          <AppLogo />
        </Link>

        <div className="my-6 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        {desktopNavigation}

        <div className="mt-6 rounded-2xl border border-border/80 bg-card/50 p-3">
          <ThemeSwitcher contained />
        </div>
        <div className="mt-3 rounded-2xl border border-primary/15 bg-primary/[0.055] p-4">
          <div className="flex items-center gap-2 text-xs font-bold text-primary">
            <span className="h-2 w-2 rounded-full bg-primary" />
            PERFORMANCE LAB ONLINE
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">Explainable pose and biomechanics analysis.</p>
        </div>
        <Button type="button" variant="ghost" className="mt-3 w-full justify-start" onClick={logout}>
          <SportIcon name="logout" className="h-4 w-4" />
          Sign out
        </Button>
      </aside>

      <header className="navigation-surface mobile-safe-top fixed inset-x-0 top-0 z-50 border-b backdrop-blur-xl lg:hidden">
        <div className="flex h-16 items-center justify-between px-4">
          <Link href="/dashboard" className="flex items-center gap-2 font-black tracking-tight">
            <AppLogo size="compact" showText={false} />
            <span>AVISHKARA</span>
          </Link>
          <div className="flex items-center gap-1"><ThemeSwitcher compact /><Button type="button" variant="ghost" size="sm" className="h-10 w-10 px-0" onClick={logout} aria-label="Sign out"><SportIcon name="logout" className="h-5 w-5" /></Button></div>
        </div>
      </header>

      <nav aria-label="Mobile dashboard navigation" className="navigation-surface mobile-safe-bottom fixed inset-x-0 bottom-0 z-50 grid grid-cols-5 border-t px-2 pt-2 shadow-[0_-16px_50px_hsl(var(--background)/0.45)] backdrop-blur-2xl lg:hidden">
        {DASHBOARD_NAVIGATION.map((item) => {
          const active = item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={cn("relative flex min-h-16 flex-col items-center justify-center gap-1 rounded-xl px-1 py-2 text-[0.66rem] font-bold text-muted-foreground transition-colors", "active:bg-primary/10", active && "bg-primary/10 text-primary")}>
              {active && <span className="absolute -top-2 h-0.5 w-8 rounded-full bg-primary shadow-glow" />}
              <SportIcon name={item.icon as SportIconName} className="h-5 w-5" />
              <span className="max-w-full truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
