"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { LeaderboardSkeleton } from "@/components/loading/page-skeletons";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SportIcon } from "@/components/ui/sport-icon";
import { StatePanel } from "@/components/ui/state-panel";
import { getApiErrorMessage } from "@/lib/api-error";
import { getLeaderboard } from "@/services/leaderboard";
import type { LeaderboardEntry, LeaderboardFilters, LeaderboardResponse } from "@/types/leaderboard";

type FilterState = {
  sport: string;
  state: string;
  gender: string;
  minAge: string;
  maxAge: string;
  minExperience: string;
  maxExperience: string;
};

const EMPTY_FILTERS: FilterState = {
  sport: "",
  state: "",
  gender: "",
  minAge: "",
  maxAge: "",
  minExperience: "",
  maxExperience: "",
};

const SPORTS = [
  { label: "Running", value: "Running" },
  { label: "Jumping", value: "Jumping" },
  { label: "Cricket Bowling", value: "Bowling" },
];
const GENDERS = ["Male", "Female", "Other"];

function toRequestFilters(filters: FilterState): LeaderboardFilters {
  const optionalNumber = (value: string) => {
    if (!value.trim()) return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  return {
    sport: filters.sport || undefined,
    state: filters.state.trim() || undefined,
    gender: filters.gender || undefined,
    min_age: optionalNumber(filters.minAge),
    max_age: optionalNumber(filters.maxAge),
    min_experience: optionalNumber(filters.minExperience),
    max_experience: optionalNumber(filters.maxExperience),
  };
}

function medal(rank: number) {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `#${rank}`;
}

function sportLabel(value: string) {
  return value === "Bowling" ? "Cricket Bowling" : value;
}

function rankStyle(rank: number) {
  if (rank === 1) {
    return {
      card: "border-yellow-300/45 bg-gradient-to-r from-yellow-300/[0.12] via-card/[0.62] to-card/[0.5] shadow-[0_20px_70px_rgba(250,204,21,0.14)]",
      badge: "border-yellow-500/45 bg-yellow-400/20 text-yellow-800 shadow-[0_0_42px_rgba(250,204,21,0.18)] dark:border-yellow-300/45 dark:bg-yellow-300/15 dark:text-yellow-200",
      score: "text-yellow-700 dark:text-yellow-200",
      label: "Champion pace",
    };
  }
  if (rank === 2) {
    return {
      card: "border-slate-300/40 bg-gradient-to-r from-slate-200/[0.1] via-card/[0.58] to-card/[0.48] shadow-[0_20px_70px_rgba(226,232,240,0.1)]",
      badge: "border-slate-500/35 bg-slate-500/10 text-slate-800 dark:border-slate-300/40 dark:bg-slate-200/10 dark:text-slate-100",
      score: "text-slate-700 dark:text-slate-100",
      label: "Podium push",
    };
  }
  if (rank === 3) {
    return {
      card: "border-orange-300/40 bg-gradient-to-r from-orange-300/[0.1] via-card/[0.58] to-card/[0.48] shadow-[0_20px_70px_rgba(251,146,60,0.1)]",
      badge: "border-orange-500/40 bg-orange-400/15 text-orange-800 dark:border-orange-300/40 dark:bg-orange-300/10 dark:text-orange-200",
      score: "text-orange-700 dark:text-orange-200",
      label: "Trial ready",
    };
  }
  return {
    card: "border-border/70 bg-card/[0.45] hover:border-primary/25 hover:bg-primary/[0.035]",
    badge: "border-primary/20 bg-primary/10 text-primary",
    score: "text-accent",
    label: "Contender",
  };
}

function LeaderboardRow({ entry }: { entry: LeaderboardEntry }) {
  const style = rankStyle(entry.rank);
  const analysisHref = entry.is_current_user
    ? `/dashboard/results/${entry.upload_id}`
    : `/leaderboard/results/${entry.upload_id}`;

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border p-4 shadow-[0_12px_36px_hsl(var(--primary)/0.04)] backdrop-blur-md transition duration-300 hover:-translate-y-0.5 ${
        entry.is_current_user
          ? "border-primary/45 bg-primary/[0.08] shadow-[0_18px_55px_hsl(var(--primary)/0.12)]"
          : style.card
      }`}
    >
      <div className="pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-primary/55 to-transparent opacity-70" />
      <div className="grid gap-4 lg:grid-cols-[6.5rem_minmax(0,1.15fr)_10rem_10rem_8rem_auto] lg:items-center">
        <div>
          <p className="metric-label">Rank</p>
          <div className="mt-2 flex items-center gap-2 lg:block">
            <div className={`inline-grid h-16 w-16 place-items-center rounded-2xl border text-2xl font-black ${style.badge}`}>
              {medal(entry.rank)}
            </div>
            <p className="text-xs font-black uppercase tracking-[0.16em] text-muted-foreground lg:mt-2">{style.label}</p>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="metric-label">Athlete</p>
            {entry.is_current_user && (
              <span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-1 text-[0.65rem] font-black uppercase tracking-wider text-primary">
                You
              </span>
            )}
          </div>
          <p className="mt-2 truncate text-lg font-black tracking-tight">{entry.name}</p>
          <p className="mt-1 text-xs text-muted-foreground">Completed {new Date(entry.completed_at).toLocaleDateString()}</p>
        </div>

        <div>
          <p className="metric-label">Sport</p>
          <p className="mt-2 rounded-full border border-border/70 bg-card/[0.48] px-3 py-2 text-sm font-black">{sportLabel(entry.sport)}</p>
        </div>

        <div>
          <p className="metric-label">State</p>
          <p className="mt-2 truncate rounded-full border border-border/70 bg-card/[0.48] px-3 py-2 text-sm font-black">{entry.state}</p>
        </div>

        <div className="rounded-2xl border border-border/70 bg-card/[0.52] px-4 py-3 text-left shadow-[inset_0_1px_0_hsl(var(--foreground)/0.04)] lg:text-center">
          <p className="metric-label">Score</p>
          <p className={`mt-1 text-3xl font-black ${style.score}`}>
            <AnimatedNumber value={entry.overall_score} decimals={1} />
          </p>
        </div>

        <Button asChild variant="outline" size="sm" className="justify-center">
          <Link href={analysisHref}>
            View analysis <SportIcon name="arrow" className="h-4 w-4" />
          </Link>
        </Button>
      </div>
    </div>
  );
}

function PodiumPreview({ entries }: Readonly<{ entries: LeaderboardEntry[] }>) {
  const podium = entries.slice(0, 3);
  if (!podium.length) return null;

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {podium.map((entry) => {
        const style = rankStyle(entry.rank);
        return (
          <div key={entry.athlete_id} className={`relative overflow-hidden rounded-2xl border p-4 ${style.card}`}>
            <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="metric-label">Top {entry.rank}</p>
                <p className="mt-2 truncate text-lg font-black">{entry.name}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{sportLabel(entry.sport)} · {entry.state}</p>
              </div>
              <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl border text-xl font-black ${style.badge}`}>
                {medal(entry.rank)}
              </span>
            </div>
            <p className={`mt-4 text-4xl font-black ${style.score}`}>
              <AnimatedNumber value={entry.overall_score} decimals={1} />
              <span className="ml-1 text-sm text-muted-foreground">/100</span>
            </p>
          </div>
        );
      })}
    </div>
  );
}

function LeaderboardHeaderRow() {
  return (
    <div className="hidden rounded-xl border border-border/70 bg-background/30 px-4 py-3 text-[0.68rem] font-black uppercase tracking-[0.18em] text-muted-foreground lg:grid lg:grid-cols-[6.5rem_minmax(0,1.15fr)_10rem_10rem_8rem_auto] lg:items-center">
      <span>Rank</span>
      <span>Athlete</span>
      <span>Sport</span>
      <span>State</span>
      <span>Score</span>
      <span className="text-right">View analysis</span>
    </div>
  );
}

export function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(EMPTY_FILTERS);

  const load = useCallback(() => {
    setError("");
    getLeaderboard(toRequestFilters(appliedFilters))
      .then(setLeaderboard)
      .catch((requestError) => setError(getApiErrorMessage(requestError)));
  }, [appliedFilters]);

  useEffect(() => {
    load();
    window.addEventListener("focus", load);
    window.addEventListener("assessment-completed", load);
    return () => {
      window.removeEventListener("focus", load);
      window.removeEventListener("assessment-completed", load);
    };
  }, [load]);

  function updateFilter(key: keyof FilterState, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function applyFilters() {
    setLeaderboard(null);
    setAppliedFilters(filters);
  }

  function resetFilters() {
    setLeaderboard(null);
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  }

  if (error) {
    return (
      <StatePanel
        tone="error"
        icon="pulse"
        title="Leaderboard could not be loaded"
        description={error}
        actionLabel="Try again"
        onAction={load}
      />
    );
  }

  if (!leaderboard) {
    return <LeaderboardSkeleton />;
  }

  return (
    <Card className="main-action-card">
      <CardHeader className="section-card-header">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="metric-label">Contest ranking</p>
            <CardTitle>National leaderboard</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              Rank, athlete, sport, state and score from completed assessments. Top 3 athletes get podium styling.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-3 py-1.5 text-xs font-black text-accent">
            <SportIcon name="pulse" className="h-4 w-4" />
            Live contest board
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-4 sm:p-6">
        <div className="rounded-2xl border border-border/70 bg-card/[0.48] p-4 shadow-[inset_0_1px_0_hsl(var(--foreground)/0.04)]">
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-7">
            <div className="space-y-2">
              <Label htmlFor="leaderboard-sport">Primary sport</Label>
              <select
                id="leaderboard-sport"
                className="h-11 w-full rounded-xl border border-input bg-background/60 px-3 text-sm font-semibold text-foreground outline-none transition focus:border-primary"
                value={filters.sport}
                onChange={(event) => updateFilter("sport", event.target.value)}
              >
                <option value="">All sports</option>
                {SPORTS.map((sport) => (
                  <option key={sport.value} value={sport.value}>{sport.label}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="leaderboard-gender">Gender</Label>
              <select
                id="leaderboard-gender"
                className="h-11 w-full rounded-xl border border-input bg-background/60 px-3 text-sm font-semibold text-foreground outline-none transition focus:border-primary"
                value={filters.gender}
                onChange={(event) => updateFilter("gender", event.target.value)}
              >
                <option value="">All genders</option>
                {GENDERS.map((gender) => (
                  <option key={gender} value={gender}>{gender}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="leaderboard-state">Region / State</Label>
              <Input id="leaderboard-state" value={filters.state} onChange={(event) => updateFilter("state", event.target.value)} placeholder="Karnataka" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="leaderboard-min-age">Min age</Label>
              <Input id="leaderboard-min-age" min={5} max={100} type="number" value={filters.minAge} onChange={(event) => updateFilter("minAge", event.target.value)} placeholder="14" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="leaderboard-max-age">Max age</Label>
              <Input id="leaderboard-max-age" min={5} max={100} type="number" value={filters.maxAge} onChange={(event) => updateFilter("maxAge", event.target.value)} placeholder="25" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="leaderboard-min-experience">Min exp.</Label>
              <Input id="leaderboard-min-experience" min={0} max={80} type="number" value={filters.minExperience} onChange={(event) => updateFilter("minExperience", event.target.value)} placeholder="1" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="leaderboard-max-experience">Max exp.</Label>
              <Input id="leaderboard-max-experience" min={0} max={80} type="number" value={filters.maxExperience} onChange={(event) => updateFilter("maxExperience", event.target.value)} placeholder="8" />
            </div>
          </div>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={resetFilters}>Reset</Button>
            <Button type="button" className="w-full sm:w-auto" onClick={applyFilters}>Apply filters</Button>
          </div>
        </div>

        {leaderboard.top_athletes.length ? (
          <>
            <PodiumPreview entries={leaderboard.top_athletes} />
            <LeaderboardHeaderRow />
            <div className="space-y-3">
              {leaderboard.top_athletes.map((entry) => (
                <LeaderboardRow key={entry.athlete_id} entry={entry} />
              ))}
            </div>
          </>
        ) : (
          <StatePanel
            compact
            icon="pulse"
            title="No ranked athletes for this filter"
            description="No completed assessments match this contest view yet. Widen the filters or analyze a new athlete video for this sport."
            actionLabel="Clear filters"
            onAction={resetFilters}
          />
        )}

        {leaderboard.current_user_entry && (
          <>
            <div className="flex items-center gap-3 py-2">
              <span className="h-px flex-1 bg-border" />
              <span className="text-[0.65rem] font-black uppercase tracking-[0.24em] text-muted-foreground">Your rank outside top 5</span>
              <span className="h-px flex-1 bg-border" />
            </div>
            <LeaderboardRow entry={leaderboard.current_user_entry} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
