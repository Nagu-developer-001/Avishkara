import { cn } from "@/lib/utils";

const LOGO_SRC = "/brand/avishkara-sports-intelligence.jpeg";

type AppLogoProps = {
  className?: string;
  imageClassName?: string;
  size?: "compact" | "sidebar" | "hero";
  showText?: boolean;
  authority?: boolean;
};

export function AppLogo({
  className,
  imageClassName,
  size = "sidebar",
  showText = true,
  authority = false,
}: Readonly<AppLogoProps>) {
  const imageSize = {
    compact: "h-10 w-10 rounded-xl",
    sidebar: "h-14 w-14 rounded-2xl",
    hero: "h-16 w-16 rounded-[1.35rem]",
  }[size];

  return (
    <span className={cn("flex min-w-0 items-center gap-3", className)}>
      <span className={cn("relative shrink-0 overflow-hidden border border-primary/25 bg-[#030712] shadow-glow", imageSize)}>
        <img
          src={LOGO_SRC}
          alt="Avishkara Sports Intelligence logo"
          className={cn("h-full w-full object-cover object-center", imageClassName)}
        />
      </span>
      {showText && (
        <span className="min-w-0">
          <span className="block truncate text-lg font-black tracking-[-0.04em]">
            {authority ? "AVISHKARA AUTHORITY" : "AVISHKARA"}
          </span>
          <span className="block truncate text-[0.62rem] font-bold uppercase tracking-[0.24em] text-primary">
            {authority ? "National Talent Intelligence" : "Sports Intelligence"}
          </span>
        </span>
      )}
    </span>
  );
}
