"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, type CSSProperties, type PointerEvent, type ReactNode } from "react";

import { cn } from "@/lib/utils";

type Falloff = "linear" | "smooth" | "sharp";

export type LineSidebarItem = {
  label: string;
  href: string;
  icon?: ReactNode;
};

type LineSidebarProps = {
  items: LineSidebarItem[];
  activeIndex: number;
  ariaLabel?: string;
  accentColor?: string;
  textColor?: string;
  markerColor?: string;
  showIndex?: boolean;
  showMarker?: boolean;
  proximityRadius?: number;
  maxShift?: number;
  falloff?: Falloff;
  markerLength?: number;
  markerGap?: number;
  tickScale?: number;
  scaleTick?: boolean;
  itemGap?: number;
  fontSize?: number;
  smoothing?: number;
  className?: string;
};

const FALLOFF_CURVES: Record<Falloff, (progress: number) => number> = {
  linear: (progress) => progress,
  smooth: (progress) => progress * progress * (3 - 2 * progress),
  sharp: (progress) => progress * progress * progress,
};

export function LineSidebar({
  items,
  activeIndex,
  ariaLabel = "Navigation",
  accentColor = "hsl(var(--primary))",
  textColor = "hsl(var(--muted-foreground))",
  markerColor = "hsl(var(--muted-foreground) / 0.42)",
  showIndex = true,
  showMarker = true,
  proximityRadius = 110,
  maxShift = 30,
  falloff = "smooth",
  markerLength = 74,
  markerGap = 0,
  tickScale = 0.5,
  scaleTick = true,
  itemGap = 18,
  fontSize = 0.95,
  smoothing = 100,
  className,
}: Readonly<LineSidebarProps>) {
  const listRef = useRef<HTMLUListElement | null>(null);
  const itemRefs = useRef<Array<HTMLLIElement | null>>([]);
  const targetsRef = useRef<number[]>([]);
  const currentRef = useRef<number[]>([]);
  const rafRef = useRef<number | null>(null);
  const lastFrameRef = useRef(0);
  const activeRef = useRef(activeIndex);
  const smoothingRef = useRef(smoothing);

  activeRef.current = activeIndex;
  smoothingRef.current = smoothing;

  const runFrame = useCallback((now: number) => {
    const delta = Math.min((now - lastFrameRef.current) / 1000, 0.05);
    lastFrameRef.current = now;
    const tau = Math.max(smoothingRef.current, 1) / 1000;
    const factor = 1 - Math.exp(-delta / tau);
    let moving = false;

    itemRefs.current.forEach((item, index) => {
      if (!item) return;

      const target = Math.max(targetsRef.current[index] ?? 0, activeRef.current === index ? 1 : 0);
      const current = currentRef.current[index] ?? 0;
      const next = current + (target - current) * factor;
      const settled = Math.abs(target - next) < 0.0015;
      const value = settled ? target : next;

      currentRef.current[index] = value;
      item.style.setProperty("--effect", value.toFixed(4));
      if (!settled) moving = true;
    });

    rafRef.current = moving ? window.requestAnimationFrame(runFrame) : null;
  }, []);

  const startLoop = useCallback(() => {
    if (rafRef.current != null) return;
    lastFrameRef.current = performance.now();
    rafRef.current = window.requestAnimationFrame(runFrame);
  }, [runFrame]);

  const handlePointerMove = useCallback(
    (event: PointerEvent<HTMLUListElement>) => {
      const list = listRef.current;
      if (!list) return;

      const rect = list.getBoundingClientRect();
      const pointerY = event.clientY - rect.top;
      const ease = FALLOFF_CURVES[falloff] ?? FALLOFF_CURVES.linear;

      itemRefs.current.forEach((item, index) => {
        if (!item) return;

        const center = item.offsetTop + item.offsetHeight / 2;
        const distance = Math.abs(pointerY - center);
        targetsRef.current[index] = ease(Math.max(0, 1 - distance / proximityRadius));
      });

      startLoop();
    },
    [falloff, proximityRadius, startLoop],
  );

  const handlePointerLeave = useCallback(() => {
    targetsRef.current = targetsRef.current.map(() => 0);
    startLoop();
  }, [startLoop]);

  const handleItemPointerEnter = useCallback(
    (index: number) => {
      targetsRef.current[index] = 1;
      startLoop();
    },
    [startLoop],
  );

  const handleItemFocus = useCallback(
    (index: number) => {
      targetsRef.current[index] = 1;
      startLoop();
    },
    [startLoop],
  );

  useEffect(() => {
    itemRefs.current.forEach((item, index) => {
      if (!item) return;

      const value = activeRef.current === index ? 1 : 0;
      currentRef.current[index] = value;
      item.style.setProperty("--effect", String(value));
    });
    startLoop();

    return () => {
      if (rafRef.current != null) window.cancelAnimationFrame(rafRef.current);
    };
  }, [activeIndex, startLoop]);

  return (
    <nav
      aria-label={ariaLabel}
      className={cn("line-sidebar", showMarker && "line-sidebar--markers", scaleTick && "line-sidebar--scale-tick", className)}
      style={
        {
          "--accent-color": accentColor,
          "--text-color": textColor,
          "--marker-color": markerColor,
          "--marker-length": `${markerLength}px`,
          "--marker-gap": `${markerGap}px`,
          "--tick-scale": tickScale,
          "--max-shift": `${maxShift}px`,
          "--item-gap": `${itemGap}px`,
          "--font-size": `${fontSize}rem`,
        } as CSSProperties
      }
    >
      <ul ref={listRef} className="line-sidebar__list" onPointerMove={handlePointerMove} onPointerLeave={handlePointerLeave}>
        {items.map((item, index) => (
          <li
            key={item.href}
            ref={(element) => {
              itemRefs.current[index] = element;
            }}
            className={cn("line-sidebar__item", activeIndex === index && "line-sidebar__item--active")}
            onPointerEnter={() => handleItemPointerEnter(index)}
          >
            {showMarker && <span className="line-sidebar__marker" aria-hidden="true" />}
            <Link
              href={item.href}
              aria-current={activeIndex === index ? "page" : undefined}
              className="line-sidebar__label"
              onFocus={() => handleItemFocus(index)}
            >
              {showIndex && <span className="line-sidebar__index">{String(index + 1).padStart(2, "0")}</span>}
              {item.icon}
              <span className="line-sidebar__text">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
