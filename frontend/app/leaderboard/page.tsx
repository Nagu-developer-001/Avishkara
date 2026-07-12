import { Leaderboard } from "@/components/dashboard/leaderboard";
import { AthleteShell } from "@/components/dashboard/athlete-shell";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageLayout, PageMainSection } from "@/components/layout/page-layout";

export default function LeaderboardPage() {
  return (
    <AthleteShell>
      <PageLayout>
        <PageHeader
          eyebrow="Contest ranking"
          title="National leaderboard"
          description="Track the top 5 athlete performances and see your own rank when you are outside the leading board."
        />
        <PageMainSection label="National leaderboard">
          <Leaderboard />
        </PageMainSection>
      </PageLayout>
    </AthleteShell>
  );
}
