"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SportIcon, type SportIconName } from "@/components/ui/sport-icon";
import { cn } from "@/lib/utils";

type StatePanelProps = {
  title: string;
  description: string;
  icon?: SportIconName;
  tone?: "empty" | "error" | "info";
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  compact?: boolean;
  className?: string;
};

export function StatePanel({ title, description, icon = "activity", tone = "empty", actionLabel, actionHref, onAction, compact = false, className }: StatePanelProps) {
  const action = actionLabel && (actionHref || onAction) ? (
    actionHref ? <Button asChild size={compact ? "sm" : "default"}><Link href={actionHref}>{actionLabel}</Link></Button> : <Button type="button" size={compact ? "sm" : "default"} onClick={onAction}>{actionLabel}</Button>
  ) : null;
  const isError = tone === "error";

  return (
    <div
      className={cn(
        "state-card relative isolate flex flex-col items-center justify-center overflow-hidden px-6 text-center",
        compact ? "min-h-40 py-6" : "min-h-64 py-10",
        isError && "border-destructive/30 bg-destructive/[0.06]",
        className,
      )}
      role={isError ? "alert" : "status"}
    >
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_50%_0%,hsl(var(--primary)/0.12),transparent_42%)]" />
      <div className="pointer-events-none absolute inset-x-8 top-0 -z-10 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
      <span
        className={cn(
          "relative grid place-items-center rounded-2xl border shadow-[0_16px_40px_hsl(var(--primary)/0.12)]",
          compact ? "h-11 w-11" : "h-16 w-16",
          isError
            ? "border-destructive/25 bg-destructive/10 text-destructive"
            : "border-primary/25 bg-primary/10 text-primary",
        )}
      >
        <span className={cn("absolute inset-0 rounded-2xl blur-xl", isError ? "bg-destructive/15" : "bg-primary/20")} />
        <SportIcon name={icon} className={cn("relative", compact ? "h-5 w-5" : "h-7 w-7")} />
      </span>
      <h3 className={cn("font-black tracking-[-0.03em] text-foreground", compact ? "mt-3 text-base" : "mt-5 text-2xl")}>{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
