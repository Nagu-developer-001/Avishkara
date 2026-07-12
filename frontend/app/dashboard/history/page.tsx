import { AssessmentHistory } from "@/components/history/assessment-history";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageLayout, PageMainSection } from "@/components/layout/page-layout";

export default function HistoryPage() {
  return (
    <PageLayout>
      <PageHeader eyebrow="Performance archive" title="Assessment history" description="Track completed analyses and revisit every phase, metric, and recommendation." />

      <PageMainSection label="Assessment history">
        <AssessmentHistory />
      </PageMainSection>
    </PageLayout>
  );
}
