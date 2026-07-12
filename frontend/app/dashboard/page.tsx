import { PageHeader } from "@/components/dashboard/page-header";
import { ProgressAnalytics } from "@/components/dashboard/progress-analytics";
import { PageLayout, PageMainSection, PageSupportingSection } from "@/components/layout/page-layout";
import { Card, CardContent } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <PageLayout>
      <PageHeader eyebrow="Athlete command centre" title="Performance dashboard" description="Capture movement. Decode biomechanics. Turn every frame into an explainable performance signal." />

      <PageMainSection label="Dashboard workflow">
        <Card className="main-action-card">
          <CardContent className="grid gap-6 p-6 sm:grid-cols-3">
            {["Capture", "Analyze", "Improve"].map((step, index) => (
              <div key={step} className="relative rounded-xl border border-border/70 bg-card/[0.48] p-4 shadow-[inset_0_1px_0_hsl(var(--foreground)/0.04)]">
                <p className="text-4xl font-black text-primary/35">0{index + 1}</p>
                <p className="-mt-2 font-bold text-foreground">{step}</p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{index === 0 ? "Upload a clear full-body sports video." : index === 1 ? "Extract pose, phases, and physical metrics." : "Review explainable scores and guidance."}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </PageMainSection>

      <PageSupportingSection label="Progress analytics">
        <ProgressAnalytics />
      </PageSupportingSection>
    </PageLayout>
  );
}
