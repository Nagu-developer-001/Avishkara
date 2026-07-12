import { AssessmentResults } from "@/components/results/assessment-results";

type ResultsPageProps = {
  params: Promise<{ uploadId: string }>;
};

export default async function ResultsPage({ params }: ResultsPageProps) {
  const { uploadId } = await params;
  return <AssessmentResults uploadId={uploadId} />;
}
