import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function HeaderSkeleton() {
  return (
    <div className="space-y-3" role="presentation">
      <Skeleton className="h-3 w-32" />
      <Skeleton className="h-10 w-full max-w-md" />
      <Skeleton className="h-4 w-64 max-w-full" />
    </div>
  );
}

function ScoreCardSkeleton() {
  return (
    <Card className="supporting-card">
      <CardContent className="space-y-5 p-6">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-12 w-28" />
        <Skeleton className="h-2 w-full rounded-full" />
      </CardContent>
    </Card>
  );
}

function FormRowsSkeleton({ rows = 5 }: Readonly<{ rows?: number }>) {
  return (
    <div className="grid gap-x-6 gap-y-7 sm:grid-cols-2">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className={index === 0 || index === rows - 1 ? "space-y-2 sm:col-span-2" : "space-y-2"}>
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-11 w-full rounded-xl" />
        </div>
      ))}
      <div className="flex justify-end border-t border-border/70 pt-6 sm:col-span-2">
        <Skeleton className="h-12 w-36 rounded-xl" />
      </div>
    </div>
  );
}

export function RouteLoadingSkeleton({ label = "Preparing workspace" }: Readonly<{ label?: string }>) {
  return (
    <main className="grid min-h-screen place-items-center bg-background p-6" role="status" aria-label={label}>
      <Card className="main-action-card w-full max-w-md">
        <CardContent className="space-y-5 p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-14 w-14 rounded-2xl" />
            <div className="flex-1 space-y-3">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-6 w-44" />
            </div>
          </div>
          <Skeleton className="h-2 w-full rounded-full" />
          <div className="grid gap-3 sm:grid-cols-3">
            {[0, 1, 2].map((item) => <Skeleton key={item} className="h-16 rounded-xl" />)}
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="content-grid xl:grid-cols-[0.72fr_1.28fr]" role="status" aria-label="Loading profile">
      <Card className="main-action-card">
        <CardContent className="space-y-7 p-7 sm:p-8">
          <div className="flex items-start justify-between">
            <Skeleton className="h-24 w-24 rounded-[2rem]" />
            <Skeleton className="h-7 w-24 rounded-full" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-4 w-36" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[0, 1, 2].map((item) => <Skeleton key={item} className="h-16 rounded-xl" />)}
          </div>
          <div className="space-y-3 border-t border-border/70 pt-6">
            <div className="flex justify-between">
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-3 w-10" />
            </div>
            <Skeleton className="h-2 w-full rounded-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </CardContent>
      </Card>

      <Card className="main-action-card">
        <CardHeader className="section-card-header">
          <div className="flex items-center gap-3">
            <Skeleton className="h-11 w-11 rounded-xl" />
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-72 max-w-full" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 lg:p-8">
          <FormRowsSkeleton />
        </CardContent>
      </Card>
    </div>
  );
}

export function ResultsSkeleton() {
  return (
    <div className="space-y-8" role="status" aria-label="Loading assessment results">
      <HeaderSkeleton />
      <div className="grid gap-4 lg:grid-cols-4">
        <Card className="main-action-card"><CardContent className="space-y-16 p-7"><Skeleton className="h-5 w-28" /><Skeleton className="h-20 w-40" /></CardContent></Card>
        <div className="grid gap-4 sm:grid-cols-3 lg:col-span-3">{[0, 1, 2].map((item) => <ScoreCardSkeleton key={item} />)}</div>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        {[0, 1].map((item) => <Card className="supporting-card" key={item}><CardHeader className="space-y-3"><Skeleton className="h-4 w-28" /><Skeleton className="h-7 w-48" /></CardHeader><CardContent><Skeleton className="aspect-video w-full rounded-xl" /></CardContent></Card>)}
      </div>
    </div>
  );
}

export function AnalyticsSkeleton() {
  return (
    <section className="space-y-5" role="status" aria-label="Loading progress analytics">
      <HeaderSkeleton />
      <div className="grid gap-4 sm:grid-cols-3">{[0, 1, 2].map((item) => <ScoreCardSkeleton key={item} />)}</div>
      <div className="grid gap-5 xl:grid-cols-2">{[0, 1].map((item) => <Card className="supporting-card" key={item}><CardHeader><Skeleton className="h-5 w-44" /></CardHeader><CardContent><Skeleton className="h-52 w-full" /></CardContent></Card>)}</div>
    </section>
  );
}

export function HistorySkeleton() {
  return (
    <div className="grid gap-4" role="status" aria-label="Loading assessment history">
      {[0, 1, 2].map((item) => (
        <Card className="supporting-card" key={item}>
          <CardContent className="flex items-center gap-4 p-6">
            <Skeleton className="h-12 w-12 shrink-0 rounded-xl" />
            <div className="min-w-0 flex-1 space-y-3">
              <Skeleton className="h-5 w-2/5" />
              <Skeleton className="h-3 w-1/3" />
            </div>
            <Skeleton className="hidden h-10 w-20 rounded-xl sm:block" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function LeaderboardSkeleton() {
  return (
    <Card className="main-action-card" role="status" aria-label="Loading leaderboard">
      <CardHeader className="section-card-header">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-3">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-4 w-96 max-w-full" />
          </div>
          <Skeleton className="h-9 w-40 rounded-full" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-4 sm:p-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
        {[0, 1, 2, 3, 4].map((item) => <Skeleton key={item} className="h-24 w-full rounded-2xl" />)}
      </CardContent>
    </Card>
  );
}

export function AuthorityDashboardSkeleton() {
  return (
    <div className="space-y-8" role="status" aria-label="Loading authority dashboard">
      <HeaderSkeleton />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((item) => <ScoreCardSkeleton key={item} />)}</div>
      <Card className="supporting-card"><CardHeader><Skeleton className="h-7 w-48" /></CardHeader><CardContent className="space-y-4">{[0, 1, 2, 3].map((item) => <Skeleton key={item} className="h-14 w-full rounded-xl" />)}</CardContent></Card>
    </div>
  );
}

export function AuthorityAssessmentSkeleton() {
  return (
    <div className="space-y-7" role="status" aria-label="Loading athlete assessment">
      <HeaderSkeleton />
      <div className="grid gap-5 xl:grid-cols-2">{[0, 1].map((item) => <Card className="main-action-card" key={item}><CardHeader><Skeleton className="h-6 w-44" /></CardHeader><CardContent><Skeleton className="aspect-video w-full rounded-xl" /></CardContent></Card>)}</div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((item) => <ScoreCardSkeleton key={item} />)}</div>
    </div>
  );
}
