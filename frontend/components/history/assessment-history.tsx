"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HistorySkeleton } from "@/components/loading/page-skeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { SportIcon } from "@/components/ui/sport-icon";
import { StatePanel } from "@/components/ui/state-panel";
import { getApiErrorMessage } from "@/lib/api-error";
import { cn } from "@/lib/utils";
import { getAssessment, getAssessmentHistory } from "@/services/assessments";
import type { AssessmentHistoryItem } from "@/types/assessment";

type TimelineItem = AssessmentHistoryItem & {
  trialNumber: number;
  previousScore: number | null;
  delta: number | null;
  tag: "Baseline" | "Improved" | "Dropped" | "Steady" | "Best Run";
};

type ScoreBreakdown = {
  technique: number | null;
  efficiency: number | null;
  balance: number | null;
};

type SportGroup = {
  sport: string;
  bestScore: number | null;
  items: TimelineItem[];
};

function displaySport(value: string) {
  return value === "Bowling" ? "Cricket Bowling" : value;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function scoreTone(score: number | null) {
  if (score == null) return "text-muted-foreground";
  if (score >= 75) return "text-lime-300";
  if (score >= 50) return "text-primary";
  return "text-amber-300";
}

function tagClass(tag: TimelineItem["tag"]) {
  if (tag === "Best Run") return "border-lime-400/30 bg-lime-400/10 text-lime-300";
  if (tag === "Improved") return "border-primary/30 bg-primary/10 text-primary";
  if (tag === "Dropped") return "border-red-400/30 bg-red-400/10 text-red-300";
  return "border-border bg-muted/40 text-muted-foreground";
}

function deltaClass(delta: number | null) {
  if (delta == null || delta === 0) return "text-muted-foreground";
  return delta > 0 ? "text-lime-300" : "text-red-300";
}

function deltaLabel(delta: number | null) {
  if (delta == null) return "Baseline";
  if (delta > 0) return "Improved";
  if (delta < 0) return "Dropped";
  return "Steady";
}

function ScoreChip({ label, value }: Readonly<{ label: string; value: number | null | undefined }>) {
  return (
    <div className="rounded-xl border border-border/80 bg-card/[0.5] px-3 py-2 shadow-[inset_0_1px_0_hsl(var(--foreground)/0.04)]">
      <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-lg font-black", scoreTone(value ?? null))}>
        {value == null ? "--" : value.toFixed(0)}
        <span className="text-[0.65rem] text-muted-foreground">/100</span>
      </p>
    </div>
  );
}

function ComparisonPanel({ item }: Readonly<{ item: TimelineItem }>) {
  return (
    <div className="mt-4 grid gap-2 rounded-2xl border border-border/80 bg-background/35 p-3 sm:grid-cols-3">
      <div>
        <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-muted-foreground">Current attempt</p>
        <p className="mt-1 text-xl font-black text-foreground">
          {item.overall_score == null ? "--" : item.overall_score.toFixed(0)}
          <span className="text-[0.65rem] text-muted-foreground">/100</span>
        </p>
      </div>
      <div>
        <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-muted-foreground">Previous attempt</p>
        <p className="mt-1 text-xl font-black text-muted-foreground">
          {item.previousScore == null ? "--" : item.previousScore.toFixed(0)}
          <span className="text-[0.65rem] text-muted-foreground">/100</span>
        </p>
      </div>
      <div>
        <p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-muted-foreground">Comparison</p>
        <p
          className={cn("mt-1 text-xl font-black", deltaClass(item.delta))}
        >
          {item.delta == null ? "Baseline" : `${item.delta >= 0 ? "+" : ""}${item.delta.toFixed(1)}`}
        </p>
        <p className="mt-1 text-[0.68rem] font-bold text-muted-foreground">
          {item.delta == null ? "First measured trial" : deltaLabel(item.delta)}
        </p>
      </div>
    </div>
  );
}

function MatchCard({
  item,
  breakdown,
}: Readonly<{
  item: TimelineItem;
  breakdown: ScoreBreakdown | undefined;
}>) {
  return (
    <article className="relative">
      <span className="absolute -left-[2.08rem] top-6 grid h-7 w-7 place-items-center rounded-full border border-primary/30 bg-background text-[0.65rem] font-black text-primary shadow-glow">
        {String(item.trialNumber).padStart(2, "0")}
      </span>

      <Card className="supporting-card group relative overflow-hidden transition hover:-translate-y-0.5 hover:border-primary/25 hover:bg-primary/[0.035]">
        <div className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-primary via-accent to-primary opacity-70 transition-opacity group-hover:opacity-100" />
        <div className="pointer-events-none absolute right-0 top-0 h-24 w-44 bg-primary/[0.06] blur-3xl" />
        <CardContent className="p-0">
          <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1.2fr)_15rem] lg:items-start">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[0.68rem] font-black uppercase tracking-[0.18em] text-primary">
                  {displaySport(item.sport)} session
                </p>
                <span className={cn("rounded-full border px-2.5 py-1 text-[0.68rem] font-bold", tagClass(item.tag))}>
                  {item.tag}
                </span>
                <span className={cn("rounded-full border border-border/70 bg-card/[0.46] px-2.5 py-1 text-[0.68rem] font-black", deltaClass(item.delta))}>
                  {item.delta == null ? "First attempt" : `${item.delta >= 0 ? "+" : ""}${item.delta.toFixed(1)} vs previous`}
                </span>
              </div>
              <p className="mt-2 truncate text-sm font-bold">{item.filename}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Trial {String(item.trialNumber).padStart(2, "0")} - {formatDate(item.upload_time)}
              </p>

              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                <ScoreChip label="Technique" value={breakdown?.technique} />
                <ScoreChip label="Efficiency" value={breakdown?.efficiency} />
                <ScoreChip label="Balance" value={breakdown?.balance} />
              </div>

              <ComparisonPanel item={item} />
            </div>

            <div className="rounded-2xl border border-primary/20 bg-primary/[0.055] p-4 shadow-[inset_0_1px_0_hsl(var(--primary)/0.08)]">
              <p className="metric-label">Overall</p>
              <p className={cn("mt-2 text-5xl font-black leading-none", scoreTone(item.overall_score))}>
                {item.overall_score?.toFixed(0) ?? "-"}
                <span className="ml-1 text-sm text-muted-foreground">/100</span>
              </p>
              <div className="mt-4 flex items-center justify-between gap-3">
                <div>
                  <p className="metric-label">Change</p>
                  <p
                    className={cn("mt-1 text-sm font-black", deltaClass(item.delta))}
                  >
                    {item.delta == null ? "First trial" : `${item.delta >= 0 ? "+" : ""}${item.delta.toFixed(1)}`}
                  </p>
                </div>
                <Button asChild variant="outline" size="sm" className="justify-center">
                  <Link href={`/dashboard/results/${item.upload_id}`}>
                    View <SportIcon name="arrow" className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </article>
  );
}

function PersonalBestCard({ item }: Readonly<{ item: AssessmentHistoryItem }>) {
  return (
    <Card className="main-action-card relative isolate bg-gradient-to-br from-card/[0.96] via-card/[0.9] to-primary/[0.06]">
      <div className="pointer-events-none absolute inset-0 z-20 bg-[radial-gradient(circle_at_82%_18%,hsl(var(--primary)/0.16),transparent_34%),linear-gradient(90deg,hsl(var(--card)/0.84),hsl(var(--card)/0.5),transparent)]" />
      <div className="pointer-events-none absolute inset-x-6 top-3 z-30 h-px bg-gradient-to-r from-transparent via-primary/70 to-transparent" />

      <CardContent className="relative z-40 grid gap-5 p-6 lg:grid-cols-[1fr_auto] lg:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="metric-label">Personal Best</p>
            <span className="rounded-full border border-lime-400/30 bg-lime-400/10 px-2.5 py-1 text-[0.68rem] font-black uppercase tracking-[0.16em] text-lime-300">Best run</span>
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-4">
            <p className={cn("text-6xl font-black leading-none", scoreTone(item.overall_score))}>
              {item.overall_score?.toFixed(1) ?? "-"}
              <span className="ml-2 text-base text-muted-foreground">/100</span>
            </p>
            <div className="pb-1">
              <p className="text-xl font-black">{displaySport(item.sport)}</p>
              <p className="mt-1 text-xs text-muted-foreground">{formatDate(item.upload_time)}</p>
            </div>
          </div>
          <p className="mt-4 truncate text-sm font-semibold text-muted-foreground">{item.filename}</p>
        </div>

        <Button asChild size="lg" className="justify-center">
          <Link href={`/dashboard/results/${item.upload_id}`}>
            Open best assessment <SportIcon name="arrow" className="h-4 w-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function JourneySummary({ items, sportGroups }: Readonly<{ items: AssessmentHistoryItem[]; sportGroups: SportGroup[] }>) {
  const latest = [...items].sort((first, second) => new Date(second.upload_time).getTime() - new Date(first.upload_time).getTime())[0];
  const completedScores = items.map((item) => item.overall_score).filter((score): score is number => score != null);
  const average = completedScores.length ? completedScores.reduce((total, score) => total + score, 0) / completedScores.length : null;

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {[
        ["Total trials", items.length.toString(), "Completed assessments"],
        ["Sports tracked", sportGroups.length.toString(), sportGroups.map((group) => displaySport(group.sport)).join(", ") || "No sports yet"],
        ["Latest score", latest?.overall_score == null ? "--" : latest.overall_score.toFixed(0), latest ? `${displaySport(latest.sport)} · Avg ${average?.toFixed(1) ?? "--"}` : "No latest attempt"],
      ].map(([label, value, helper]) => (
        <Card className="supporting-card" key={label}>
          <CardContent className="p-4">
            <p className="metric-label">{label}</p>
            <p className="mt-2 text-3xl font-black text-primary">{value}</p>
            <p className="mt-1 truncate text-xs text-muted-foreground">{helper}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function AssessmentHistory() {
  const [items, setItems] = useState<AssessmentHistoryItem[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [expandedSports, setExpandedSports] = useState<Record<string, boolean>>({});
  const [scoreBreakdowns, setScoreBreakdowns] = useState<Record<string, ScoreBreakdown>>({});

  const loadHistory = useCallback(() => {
    setError("");
    getAssessmentHistory()
      .then(setItems)
      .catch((requestError) => {
        setError(getApiErrorMessage(requestError));
      });
  }, []);

  useEffect(() => {
    loadHistory();
    window.addEventListener("focus", loadHistory);
    window.addEventListener("assessment-completed", loadHistory);
    return () => {
      window.removeEventListener("focus", loadHistory);
      window.removeEventListener("assessment-completed", loadHistory);
    };
  }, [loadHistory]);

  const sportGroups = useMemo<SportGroup[]>(() => {
    if (!items) return [];
    const normalizedQuery = query.trim().toLowerCase();
    const grouped = new Map<string, AssessmentHistoryItem[]>();

    items
      .filter((item) => {
        if (!normalizedQuery) return true;
        return `${item.filename} ${item.sport}`.toLowerCase().includes(normalizedQuery);
      })
      .forEach((item) => {
        grouped.set(item.sport, [...(grouped.get(item.sport) ?? []), item]);
      });

    return Array.from(grouped.entries())
      .sort(([firstSport], [secondSport]) => firstSport.localeCompare(secondSport))
      .map(([sport, sportItems]) => {
        const sortedItems = [...sportItems].sort(
          (first, second) => new Date(first.upload_time).getTime() - new Date(second.upload_time).getTime(),
        );
        const bestScore = Math.max(...sortedItems.map((item) => item.overall_score ?? -1));
        let previousScore: number | null = null;

        const timelineItems = sortedItems.map((item, index) => {
          const score = item.overall_score;
          const previousAttemptScore = previousScore;
          const delta = score != null && previousAttemptScore != null ? score - previousAttemptScore : null;
          const isBest = score != null && score === bestScore;
          const tag: TimelineItem["tag"] = isBest
            ? "Best Run"
            : delta == null
              ? "Baseline"
              : delta > 0
                ? "Improved"
                : delta < 0
                  ? "Dropped"
                  : "Steady";

          if (score != null) previousScore = score;

          return {
            ...item,
            trialNumber: index + 1,
            previousScore: previousAttemptScore,
            delta,
            tag,
          };
        });

        return { sport, bestScore: bestScore < 0 ? null : bestScore, items: timelineItems };
      });
  }, [items, query]);

  const personalBest = useMemo(() => {
    if (!items?.length) return null;
    return items.reduce<AssessmentHistoryItem | null>((best, item) => {
      if (item.overall_score == null) return best;
      if (!best || best.overall_score == null || item.overall_score > best.overall_score) return item;
      return best;
    }, null);
  }, [items]);

  const visibleItems = useMemo(
    () =>
      sportGroups.flatMap((group) => {
        const expanded = expandedSports[group.sport] ?? false;
        return expanded ? group.items : group.items.slice(-5);
      }),
    [expandedSports, sportGroups],
  );

  useEffect(() => {
    const missingItems = visibleItems.filter((item) => !scoreBreakdowns[item.upload_id]);
    if (!missingItems.length) return;

    let cancelled = false;
    Promise.all(
      missingItems.map(async (item) => {
        const detail = await getAssessment(item.upload_id);
        return {
          uploadId: item.upload_id,
          scores: {
            technique: detail.scores.technique_score,
            efficiency: detail.scores.efficiency_score,
            balance: detail.scores.balance_score,
          },
        };
      }),
    )
      .then((results) => {
        if (cancelled) return;
        setScoreBreakdowns((current) => {
          const next = { ...current };
          results.forEach((result) => {
            next[result.uploadId] = result.scores;
          });
          return next;
        });
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [scoreBreakdowns, visibleItems]);

  if (error) {
    return (
      <StatePanel
        tone="error"
        icon="history"
        title="Assessment history is unavailable"
        description={error}
        actionLabel="Try again"
        onAction={loadHistory}
      />
    );
  }

  if (!items) return <HistorySkeleton />;

  if (!items.length) {
    return (
      <StatePanel
        icon="history"
        title="Your performance timeline is empty"
        description="Start with one clear full-body sports video. Once the analysis finishes, your trials, scores, and improvement story will appear here."
        actionLabel="Start an assessment"
        actionHref="/dashboard/upload"
      />
    );
  }

  return (
    <section className="space-y-6">
      <Card className="supporting-card">
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="metric-label">Athlete journey</p>
            <h2 className="mt-1 text-2xl font-black">Sport-wise performance timeline</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Each sport keeps its own trial story, latest attempts, and progress comparison.
            </p>
          </div>

          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search video or sport"
            className="h-11 rounded-xl border border-input bg-card/70 px-3 text-sm outline-none transition focus:border-primary/50 focus:ring-2 focus:ring-primary/15 lg:w-80"
          />
        </CardContent>
      </Card>

      <JourneySummary items={items} sportGroups={sportGroups} />

      {personalBest && <PersonalBestCard item={personalBest} />}

      {sportGroups.map((group) => {
        const expanded = expandedSports[group.sport] ?? false;
        const visibleGroupItems = expanded ? group.items : group.items.slice(-5);
        const hiddenCount = Math.max(group.items.length - visibleGroupItems.length, 0);

        return (
          <section key={group.sport} className="space-y-4 rounded-[1.35rem] border border-border/70 bg-card/[0.26] p-4 sm:p-5">
            <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border/70 pb-4">
              <div>
                <p className="metric-label">Latest {Math.min(5, group.items.length)} attempts</p>
                <h3 className="mt-1 text-2xl font-black">{displaySport(group.sport)}</h3>
              </div>
              <div className="flex items-center gap-3 text-right">
                <div>
                  <p className="metric-label">Best</p>
                  <p className="text-xl font-black text-primary">{group.bestScore?.toFixed(0) ?? "-"}/100</p>
                </div>
                <div>
                  <p className="metric-label">Trials</p>
                  <p className="text-xl font-black">{group.items.length}</p>
                </div>
              </div>
            </div>

            <div className="relative space-y-4 pl-8">
              <span className="absolute bottom-8 left-[1.06rem] top-8 w-px bg-gradient-to-b from-primary/20 via-primary/55 to-primary/20" />

              {visibleGroupItems.map((item) => (
                <MatchCard key={item.upload_id} item={item} breakdown={scoreBreakdowns[item.upload_id]} />
              ))}
            </div>

            {group.items.length > 5 && (
              <div className="flex justify-center">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setExpandedSports((current) => ({ ...current, [group.sport]: !expanded }))}
                >
                  {expanded ? `Show latest 5 ${group.sport} attempts` : `Show ${hiddenCount} earlier ${group.sport} attempt${hiddenCount === 1 ? "" : "s"}`}
                  <SportIcon name="arrow" className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")} />
                </Button>
              </div>
            )}
          </section>
        );
      })}

      {!sportGroups.length && (
        <StatePanel
          compact
          icon="history"
          title="No trials match this search"
          description="Clear the search or try the sport name, video filename, or another keyword from your assessment history."
        />
      )}
    </section>
  );
}
