"use client";

import { THEMES } from "@/constants/themes";
import { useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

type ThemeSwitcherProps = {
  compact?: boolean;
  contained?: boolean;
};

export function ThemeSwitcher({ compact = false, contained = false }: Readonly<ThemeSwitcherProps>) {
  const { theme, setTheme } = useTheme();
  const selected = THEMES.find((item) => item.id === theme) ?? THEMES[0];
  const nextTheme = theme === "broadcast-sports" ? "olympic-minimal" : "broadcast-sports";

  return (
    <button
      type="button"
      onClick={() => setTheme(nextTheme)}
      className={cn(
        "theme-trigger flex items-center gap-3 rounded-xl border border-border bg-card/70 px-3 py-2.5 text-left transition hover:border-primary/35 hover:bg-primary/[0.06]",
        contained && "w-full",
        compact && "w-auto px-3",
      )}
      aria-label={`Switch display mode. Current mode: ${selected.name}`}
      title={`Current mode: ${selected.name}`}
    >
      <span className="flex shrink-0 overflow-hidden rounded-full border border-border">
        {selected.swatches.map((color) => (
          <span key={color} className="h-3.5 w-3.5" style={{ background: color }} />
        ))}
      </span>
      {!compact && (
        <span className="min-w-0 flex-1">
          <span className="block text-[0.6rem] font-bold uppercase tracking-[0.18em] text-muted-foreground">Display mode</span>
          <span className="block truncate text-xs font-bold">{selected.shortName}</span>
        </span>
      )}
      <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.62rem] font-black uppercase tracking-[0.14em] text-primary">
        {theme === "broadcast-sports" ? "Dark" : "Light"}
      </span>
    </button>
  );
}
