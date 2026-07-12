"use client";

import { Hyperspeed } from "@/components/ui/hyperspeed";
import { hyperspeedPresets } from "@/components/ui/hyperspeed-presets";
import { cn } from "@/lib/utils";

type SportsBackdropProps = {
  className?: string;
  overlayClassName?: string;
};

export function SportsBackdrop({ className, overlayClassName }: SportsBackdropProps) {
  return (
    <div className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)} aria-hidden="true">
      <div className="absolute inset-0 bg-black" />
      <Hyperspeed effectOptions={hyperspeedPresets.one} />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_42%,transparent_0%,rgba(0,0,0,0.1)_38%,rgba(0,0,0,0.72)_100%)]" />
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-r from-black/74 via-black/28 to-transparent",
          overlayClassName,
        )}
      />
    </div>
  );
}
