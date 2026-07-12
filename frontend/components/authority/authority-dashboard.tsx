"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageLayout, PageMainSection, PageSupportingSection } from "@/components/layout/page-layout";
import { AuthorityDashboardSkeleton } from "@/components/loading/page-skeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import { getApiErrorMessage } from "@/lib/api-error";
import { getAuthorityDashboard } from "@/services/authority";
import type { AuthorityDashboard as DashboardData, AuthorityFilters } from "@/types/authority";

const inputClass = "h-11 rounded-xl border border-border bg-background/35 px-3 text-sm outline-none transition focus:border-primary/40";

export function AuthorityDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [filters, setFilters] = useState<AuthorityFilters>({});
  const [draft, setDraft] = useState({ sport: "", state: "", minAge: "", maxAge: "", minScore: "", maxScore: "", shortlisted: "all" });
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    getAuthorityDashboard(filters).then(setData).catch((requestError) => setError(getApiErrorMessage(requestError)));
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  function applyFilters(event: React.FormEvent) {
    event.preventDefault();
    setFilters({
      sport: draft.sport || undefined,
      state: draft.state || undefined,
      min_age: draft.minAge ? Number(draft.minAge) : undefined,
      max_age: draft.maxAge ? Number(draft.maxAge) : undefined,
      min_score: draft.minScore ? Number(draft.minScore) : undefined,
      max_score: draft.maxScore ? Number(draft.maxScore) : undefined,
      shortlisted: draft.shortlisted === "all" ? undefined : draft.shortlisted === "yes",
    });
  }

  function resetFilters() {
    setDraft({ sport: "", state: "", minAge: "", maxAge: "", minScore: "", maxScore: "", shortlisted: "all" });
    setFilters({});
  }

  if (error) return <StatePanel tone="error" icon="dashboard" title="Talent dashboard could not be loaded" description={error} actionLabel="Try again" onAction={load} />;
  if (!data) return <AuthorityDashboardSkeleton />;

  return (
    <PageLayout>
      <div>
        <p className="metric-label">National talent command</p>
        <h1 className="mt-2 text-4xl font-black tracking-[-0.045em] sm:text-5xl">Authority Dashboard</h1>
        <p className="mt-3 text-muted-foreground">Review completed athlete assessments and identify candidates for trials.</p>
      </div>

      <PageMainSection className="content-grid sm:grid-cols-3" label="Authority summary">
        {[
          ["Total athletes", data.summary.total_athletes],
          ["Total assessments", data.summary.total_assessments],
          ["Average overall score", data.summary.average_overall_score?.toFixed(1) ?? "—"],
        ].map(([label, value]) => (
          <Card className="main-action-card" key={label}>
            <CardContent className="p-6">
              <p className="metric-label">{label}</p>
              <p className="mt-3 text-4xl font-black text-primary">{value}</p>
            </CardContent>
          </Card>
        ))}
      </PageMainSection>

      <PageSupportingSection label="Authority discovery tools">
        <Card className="supporting-card">
          <CardHeader className="section-card-header">
            <p className="metric-label">Latest activity</p>
            <CardTitle>Recently completed assessments</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {data.recent_assessments.map((item) => (
              <Link key={item.assessment_id} href={`/authority/assessments/${item.assessment_id}`} className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4 transition hover:border-primary/30">
                <p className="truncate font-bold">{item.athlete_name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{item.sport}</p>
                <p className="mt-4 text-3xl font-black text-primary">{item.overall_score.toFixed(0)}</p>
              </Link>
            ))}
            {!data.recent_assessments.length && <StatePanel compact icon="history" title="No completed assessments yet" description="Once athletes upload and complete analysis, the latest trial-ready assessments will appear here." className="md:col-span-2 xl:col-span-5" />}
          </CardContent>
        </Card>

        <Card className="supporting-card">
          <CardHeader className="section-card-header">
            <p className="metric-label">Discovery filters</p>
            <CardTitle>Find athletes</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={applyFilters} className="grid gap-3 md:grid-cols-4 xl:grid-cols-8">
              <select className={inputClass} value={draft.sport} onChange={(event) => setDraft({ ...draft, sport: event.target.value })}><option value="">All sports</option><option>Running</option><option>Jumping</option><option value="Bowling">Cricket Bowling</option></select>
              <input className={inputClass} placeholder="State" value={draft.state} onChange={(event) => setDraft({ ...draft, state: event.target.value })} />
              <input className={inputClass} type="number" min="5" max="100" placeholder="Min age" value={draft.minAge} onChange={(event) => setDraft({ ...draft, minAge: event.target.value })} />
              <input className={inputClass} type="number" min="5" max="100" placeholder="Max age" value={draft.maxAge} onChange={(event) => setDraft({ ...draft, maxAge: event.target.value })} />
              <input className={inputClass} type="number" min="0" max="100" placeholder="Min score" value={draft.minScore} onChange={(event) => setDraft({ ...draft, minScore: event.target.value })} />
              <input className={inputClass} type="number" min="0" max="100" placeholder="Max score" value={draft.maxScore} onChange={(event) => setDraft({ ...draft, maxScore: event.target.value })} />
              <select className={inputClass} value={draft.shortlisted} onChange={(event) => setDraft({ ...draft, shortlisted: event.target.value })}><option value="all">All athletes</option><option value="yes">Shortlisted</option><option value="no">Not shortlisted</option></select>
              <Button type="submit">Apply filters</Button>
            </form>
          </CardContent>
        </Card>

        <Card className="supporting-card">
          <CardHeader className="section-card-header">
            <p className="metric-label">Athlete registry</p>
            <CardTitle>{data.athletes.length} matching athletes</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            {data.athletes.length > 0 && (
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-y border-white/[0.08] text-xs uppercase tracking-wider text-muted-foreground">
                  <tr><th className="px-6 py-4">Athlete</th><th>Sport</th><th>State</th><th>Age</th><th>Latest score</th><th>Status</th><th></th></tr>
                </thead>
                <tbody>
                  {data.athletes.map((athlete) => (
                    <tr key={athlete.athlete_id} className="border-b border-white/[0.06] last:border-0">
                      <td className="px-6 py-5 font-bold">{athlete.name}</td>
                      <td>{athlete.sport}</td>
                      <td>{athlete.state}</td>
                      <td>{athlete.age}</td>
                      <td className="text-xl font-black text-primary">{athlete.latest_score.toFixed(1)}</td>
                      <td>{athlete.shortlisted ? <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">Shortlisted</span> : <span className="text-muted-foreground">Review</span>}</td>
                      <td className="pr-6 text-right"><Button asChild variant="outline" size="sm"><Link href={`/authority/assessments/${athlete.assessment_id}`}>View assessment</Link></Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {!data.athletes.length && <StatePanel compact icon="profile" title="No athletes in this selection" description="Broaden the sport, state, age, shortlist or score filters to discover more candidates." actionLabel="Clear filters" onAction={resetFilters} className="m-5" />}
          </CardContent>
        </Card>
      </PageSupportingSection>
    </PageLayout>
  );
}
