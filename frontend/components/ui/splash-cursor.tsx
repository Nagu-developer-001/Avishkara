"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

type SplashCursorProps = {
  DENSITY_DISSIPATION?: number;
  VELOCITY_DISSIPATION?: number;
  PRESSURE?: number;
  CURL?: number;
  SPLAT_RADIUS?: number;
  SPLAT_FORCE?: number;
  COLOR_UPDATE_SPEED?: number;
  SHADING?: boolean;
  RAINBOW_MODE?: boolean;
  COLOR?: string;
  className?: string;
};

type Splat = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  age: number;
  life: number;
  hue: number;
  color: string;
};

function hexToRgb(hex: string) {
  const normalized = hex.replace("#", "");
  const value = normalized.length === 3 ? normalized.replace(/(.)/g, "$1$1") : normalized;
  const parsed = Number.parseInt(value, 16);

  if (Number.isNaN(parsed)) {
    return { r: 168, g: 85, b: 247 };
  }

  return {
    r: (parsed >> 16) & 255,
    g: (parsed >> 8) & 255,
    b: parsed & 255,
  };
}

export function SplashCursor({
  DENSITY_DISSIPATION = 4.5,
  VELOCITY_DISSIPATION = 2,
  PRESSURE = 0.15,
  CURL = 3,
  SPLAT_RADIUS = 0.2,
  SPLAT_FORCE = 6000,
  COLOR_UPDATE_SPEED = 10,
  SHADING = true,
  RAINBOW_MODE = false,
  COLOR = "#A855F7",
  className,
}: Readonly<SplashCursorProps>) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext("2d", { alpha: true });
    if (!context) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const splats: Splat[] = [];
    const baseColor = hexToRgb(COLOR);
    const spawnInterval = Math.max(90, 900 / COLOR_UPDATE_SPEED);
    let animationFrame = 0;
    let lastFrame = performance.now();
    let lastSpawn = 0;
    let width = 0;
    let height = 0;
    let phase = Math.random() * Math.PI * 2;

    const resize = () => {
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      canvas.width = Math.floor(width * pixelRatio);
      canvas.height = Math.floor(height * pixelRatio);
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    };

    const makeColor = (hue: number, alpha: number) => {
      if (RAINBOW_MODE) {
        return `hsla(${hue}, 92%, 62%, ${alpha})`;
      }

      return `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, ${alpha})`;
    };

    const spawn = (time: number) => {
      phase += 0.38 + CURL * 0.012;
      const drift = Math.sin(time * 0.00035);
      const x = width * (0.18 + 0.64 * ((Math.sin(phase) + 1) / 2));
      const y = height * (0.22 + 0.58 * ((Math.cos(phase * 0.73 + drift) + 1) / 2));
      const force = SPLAT_FORCE / 6000;
      const radius = Math.max(18, Math.min(width, height) * SPLAT_RADIUS * (0.2 + PRESSURE));
      const hue = (time / 18 + phase * 45) % 360;

      splats.push({
        x,
        y,
        vx: Math.cos(phase * 1.9) * force * 18,
        vy: Math.sin(phase * 1.4) * force * 12,
        radius,
        age: 0,
        life: 1200 + DENSITY_DISSIPATION * 180,
        hue,
        color: makeColor(hue, 1),
      });
    };

    const paintStatic = () => {
      context.clearRect(0, 0, width, height);
      const gradient = context.createRadialGradient(width * 0.5, height * 0.45, 0, width * 0.5, height * 0.45, width * 0.75);
      gradient.addColorStop(0, `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.34)`);
      gradient.addColorStop(0.45, `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.12)`);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
      context.fillStyle = gradient;
      context.fillRect(0, 0, width, height);
    };

    const draw = (time: number) => {
      const delta = Math.min(32, time - lastFrame);
      lastFrame = time;

      context.globalCompositeOperation = "destination-out";
      context.fillStyle = `rgba(0, 0, 0, ${Math.min(0.24, 0.032 * DENSITY_DISSIPATION)})`;
      context.fillRect(0, 0, width, height);

      if (time - lastSpawn > spawnInterval) {
        spawn(time);
        lastSpawn = time;
      }

      context.globalCompositeOperation = "lighter";

      for (let index = splats.length - 1; index >= 0; index -= 1) {
        const splat = splats[index];
        splat.age += delta;
        splat.x += splat.vx * (delta / 16);
        splat.y += splat.vy * (delta / 16);
        splat.vx *= 1 - Math.min(0.08, VELOCITY_DISSIPATION * 0.006);
        splat.vy *= 1 - Math.min(0.08, VELOCITY_DISSIPATION * 0.006);

        const progress = splat.age / splat.life;
        if (progress >= 1) {
          splats.splice(index, 1);
          continue;
        }

        const alpha = Math.max(0, 1 - progress);
        const radius = splat.radius * (1 + progress * (2.6 + PRESSURE));
        const gradient = context.createRadialGradient(splat.x, splat.y, 0, splat.x, splat.y, radius);
        gradient.addColorStop(0, makeColor(splat.hue, 0.46 * alpha));
        gradient.addColorStop(0.42, makeColor(splat.hue, 0.18 * alpha));
        gradient.addColorStop(1, makeColor(splat.hue, 0));

        context.fillStyle = gradient;
        context.beginPath();
        context.arc(splat.x, splat.y, radius, 0, Math.PI * 2);
        context.fill();

        if (SHADING) {
          context.strokeStyle = makeColor(splat.hue, 0.16 * alpha);
          context.lineWidth = 1;
          context.beginPath();
          context.arc(splat.x + radius * 0.08, splat.y - radius * 0.08, radius * 0.52, 0, Math.PI * 2);
          context.stroke();
        }
      }

      animationFrame = window.requestAnimationFrame(draw);
    };

    resize();

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);

    if (reducedMotion) {
      paintStatic();
    } else {
      animationFrame = window.requestAnimationFrame(draw);
    }

    return () => {
      window.cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
    };
  }, [
    COLOR,
    COLOR_UPDATE_SPEED,
    CURL,
    DENSITY_DISSIPATION,
    PRESSURE,
    RAINBOW_MODE,
    SHADING,
    SPLAT_FORCE,
    SPLAT_RADIUS,
    VELOCITY_DISSIPATION,
  ]);

  return <canvas ref={canvasRef} aria-hidden="true" className={cn("pointer-events-none absolute inset-0 h-full w-full", className)} />;
}
