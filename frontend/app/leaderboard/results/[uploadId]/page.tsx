import { AthleteShell } from "@/components/dashboard/athlete-shell";
import { AssessmentResults } from "@/components/results/assessment-results";

type LeaderboardResultsPageProps = {
  params: Promise<{ uploadId: string }>;
};

export default async function LeaderboardResultsPage({ params }: LeaderboardResultsPageProps) {
  const { uploadId } = await params;

  return (
    <AthleteShell>
      <AssessmentResults uploadId={uploadId} mode="leaderboard" />
    </AthleteShell>
  );
}
