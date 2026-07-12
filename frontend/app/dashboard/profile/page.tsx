import { AthleteProfile } from "@/components/profile/athlete-profile";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageLayout, PageMainSection } from "@/components/layout/page-layout";

export default function ProfilePage() {
  return (
    <PageLayout>
      <PageHeader eyebrow="Athlete identity" title="Performance profile" description="Keep your athlete details current so every assessment carries the right sporting context." />
      <PageMainSection label="Athlete profile">
        <AthleteProfile />
      </PageMainSection>
    </PageLayout>
  );
}
