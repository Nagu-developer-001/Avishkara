import { VideoUploader } from "@/components/upload/video-uploader";
import { PageHeader } from "@/components/dashboard/page-header";
import { PageLayout, PageMainSection } from "@/components/layout/page-layout";

export default function UploadPage() {
  return (
    <PageLayout>
      <PageHeader eyebrow="New assessment" title="Analyze a performance" description="Upload a clear, full-body sports video. Avishkara validates the action before extracting phases and biomechanics." />
      <PageMainSection label="Video upload and analysis">
        <VideoUploader />
      </PageMainSection>
    </PageLayout>
  );
}
