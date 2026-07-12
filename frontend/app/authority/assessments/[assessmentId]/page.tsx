import { AthleteAssessment } from "@/components/authority/athlete-assessment";

type AuthorityAssessmentPageProps = {
  params: Promise<{ assessmentId: string }>;
};

export default async function AuthorityAssessmentPage({ params }: AuthorityAssessmentPageProps) {
  const { assessmentId } = await params;
  return <AthleteAssessment assessmentId={assessmentId} />;
}
