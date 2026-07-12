"use client";

import { useEffect, useRef, useState } from "react";

type AnimatedNumberProps = { value: number; decimals?: number; duration?: number; prefix?: string; className?: string };

export function AnimatedNumber({ value, decimals = 0, duration = 900, prefix = "", className }: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const elementRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      if (reduceMotion) return setDisplayValue(value);
      const startedAt = performance.now();
      const animate = (time: number) => {
        const progress = Math.min((time - startedAt) / duration, 1);
        setDisplayValue(value * (1 - Math.pow(1 - progress, 3)));
        if (progress < 1) frame = requestAnimationFrame(animate);
      };
      frame = requestAnimationFrame(animate);
    }, { threshold: 0.25 });
    observer.observe(element);
    return () => { observer.disconnect(); cancelAnimationFrame(frame); };
  }, [duration, value]);

  return <span ref={elementRef} className={className}>{prefix}{displayValue.toFixed(decimals)}</span>;
}
