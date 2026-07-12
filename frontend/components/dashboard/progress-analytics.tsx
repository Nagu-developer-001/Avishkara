"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AnalyticsSkeleton } from "@/components/loading/page-skeletons";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import { getApiErrorMessage } from "@/lib/api-error";
import { getAthleteProgress } from "@/services/assessments";
import type { AthleteProgressAnalytics, ProgressTrendPoint } from "@/types/progress";

type MetricKey = "overall_score" | "technique_score" | "efficiency_score" | "balance_score";
type TrendChartProps = {
  title: string;
  metric: MetricKey;
  data: ProgressTrendPoint[];
  color: string;
};

function TrendChart({ title, metric, data, color }: TrendChartProps) {
  const width = 640;
  const height = 210;
  const padding = 34;
  const points = data.map((point, index) => {
    const x = data.length === 1 ? width / 2 : padding + (index / (data.length - 1)) * (width - padding * 2);
    const y = padding + ((100 - point[metric]) / 100) * (height - padding * 2);
    return { x, y, value: point[metric], uploadTime: point.upload_time };
  });
  const path = points.map(({ x, y }) => `${x},${y}`).join(" ");
  const firstValue = points[0]?.value ?? 0;
  const latestValue = points[points.length - 1]?.value ?? 0;
  const delta = latestValue - firstValue;
  const areaPath =
    points.length > 1
      ? `${points.map(({ x, y }, index) => `${index === 0 ? "M" : "L"} ${x} ${y}`).join(" ")} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`
      : "";

  return (
    <Card className="supporting-card bg-gradient-to-br from-card/[0.92] via-card/[0.86] to-primary/[0.04]">
      <CardHeader className="section-card-header px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base">{title}</CardTitle>
          <div className="text-right">
            <p className="text-sm font-black text-foreground">{latestValue.toFixed(1)}</p>
            <p className={delta >= 0 ? "text-[11px] font-bold text-lime-300" : "text-[11px] font-bold text-red-300"}>
              {delta >= 0 ? "+" : ""}
              {delta.toFixed(1)}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="min-h-[210px] w-full overflow-visible"
          role="img"
          aria-label={`${title} across ${data.length} assessments`}
        >
          {[0, 25, 50, 75, 100].map((value) => {
            const y = padding + ((100 - value) / 100) * (height - padding * 2);
            return (
              <g key={value}>
                <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="hsl(var(--border) / 0.42)" strokeDasharray="4 10" />
                <text x={0} y={y + 4} fill="hsl(var(--muted-foreground))" fontSize="10">
                  {value}
                </text>
              </g>
            );
          })}
          {points.map((point) => (
            <line
              key={`${point.uploadTime}-vertical`}
              x1={point.x}
              y1={padding}
              x2={point.x}
              y2={height - padding}
              stroke="hsl(var(--border) / 0.28)"
              strokeDasharray="2 10"
            />
          ))}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="hsl(var(--foreground) / 0.18)" />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="hsl(var(--foreground) / 0.18)" />
          {areaPath && <path d={areaPath} fill={color} opacity="0.1" />}
          {points.length > 1 && (
            <polyline
              className="trend-line"
              pathLength="1"
              points={path}
              fill="none"
              stroke={color}
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
          {points.length === 1 && (
            <line
              x1={padding}
              y1={points[0].y}
              x2={width - padding}
              y2={points[0].y}
              stroke={color}
              strokeDasharray="6 10"
              strokeOpacity="0.75"
              strokeWidth="1.4"
            />
          )}
          {points.map((point, index) => (
            <g
              className="trend-point"
              key={point.uploadTime}
              style={{ animationDelay: `${350 + index * 90}ms`, transformOrigin: `${point.x}px ${point.y}px` }}
            >
              <circle cx={point.x} cy={point.y} r="7" fill="hsl(var(--background))" stroke={color} strokeWidth="2.4" />
              <circle cx={point.x} cy={point.y} r="13" fill={color} opacity="0.12" />
              <text
                x={point.x}
                y={point.y - 16}
                textAnchor="middle"
                fill="hsl(var(--foreground))"
                fontSize="11"
                fontWeight="700"
              >
                {point.value.toFixed(0)}
              </text>
              <title>{`${new Date(point.uploadTime).toLocaleDateString()}: ${point.value.toFixed(1)}`}</title>
          </g>
          ))}
        </svg>
        <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
          <span>{new Date(data[0].upload_time).toLocaleDateString()}</span>
          <span>
            {data.length === 1 ? "Baseline recorded" : `${firstValue.toFixed(1)} to ${latestValue.toFixed(1)}`}
          </span>
          <span>{new Date(data[data.length - 1].upload_time).toLocaleDateString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function ProgressAnalytics() {
  const [analytics, setAnalytics] = useState<AthleteProgressAnalytics | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    getAthleteProgress()
      .then(setAnalytics)
      .catch((requestError) => setError(getApiErrorMessage(requestError)));
  }, []);

  useEffect(() => {
    load();
    window.addEventListener("focus", load);
    window.addEventListener("assessment-completed", load);
    return () => {
      window.removeEventListener("focus", load);
      window.removeEventListener("assessment-completed", load);
    };
  }, [load]);

  const summary = useMemo(() => {
    if (!analytics) return [];
    const improvement = analytics.improvement;
    return [
      { label: "Average score", value: analytics.average_score, prefix: "", description: "Across all completed assessments" },
      { label: "Best score", value: analytics.best_score, prefix: "", description: "Highest recorded overall score" },
      {
        label: "Improvement",
        value: improvement,
        prefix: improvement != null && improvement >= 0 ? "+" : "",
        description: "Latest overall score versus first",
      },
    ];
  }, [analytics]);

  if (error) {
    return (
      <StatePanel
        tone="error"
        icon="pulse"
        title="Progress could not be loaded"
        description={error}
        actionLabel="Try again"
        onAction={load}
      />
    );
  }

  if (!analytics) return <AnalyticsSkeleton />;

  if (!analytics.trend.length) {
    return (
      <StatePanel
        icon="pulse"
        title="No progress trend yet"
        description="Complete your first assessment to create a baseline. After multiple trials, this area will show score movement, technique trend, efficiency trend, and balance trend."
        actionLabel="Upload a video"
        actionHref="/dashboard/upload"
      />
    );
  }

  return (
    <section className="section-stack">
      <div>
        <p className="metric-label">Longitudinal performance</p>
        <h2 className="mt-2 text-2xl font-black tracking-tight sm:text-3xl">Athlete progress analytics</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Based on {analytics.assessment_count} completed assessment{analytics.assessment_count === 1 ? "" : "s"},
          ordered from oldest to newest.
        </p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
          {summary.map(({ label, value, prefix, description }) => (
            <Card key={label} className="supporting-card bg-gradient-to-br from-primary/[0.08] to-card/[0.88]">
              <CardContent className="p-5">
                <p className="metric-label">{label}</p>
                <p className="mt-2 text-3xl font-black text-primary">
                  {value == null ? "-" : <AnimatedNumber value={value} decimals={1} prefix={prefix} />}
                  <span className="text-sm text-muted-foreground">/100</span>
                </p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{description}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <TrendChart title="Overall improvement" metric="overall_score" data={analytics.trend} color="#a3e635" />
          <TrendChart title="Technique trend" metric="technique_score" data={analytics.trend} color="#22d3ee" />
          <TrendChart title="Efficiency trend" metric="efficiency_score" data={analytics.trend} color="#f59e0b" />
          <TrendChart title="Balance trend" metric="balance_score" data={analytics.trend} color="#c084fc" />
        </div>
      </div>
    </section>
  );
}
