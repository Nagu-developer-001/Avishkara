"use client";

import { useEffect, useState } from "react";

import { PageLayout, PageMainSection, PageSupportingSection } from "@/components/layout/page-layout";
import { AuthorityAssessmentSkeleton } from "@/components/loading/page-skeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import { getApiErrorMessage } from "@/lib/api-error";
import { getAuthorityAnnotatedVideo, getAuthorityAssessment, getAuthorityAssessmentReport, getAuthorityVideo, shortlistAthlete } from "@/services/authority";
import type { AuthorityAssessment } from "@/types/authority";

export function AthleteAssessment({ assessmentId }: { assessmentId: string }) {
  const [assessment, setAssessment] = useState<AuthorityAssessment | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [annotatedUrl, setAnnotatedUrl] = useState<string | null>(null);
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);

  useEffect(() => {
    let active = true;
    let originalObjectUrl: string | null = null;
    let annotatedObjectUrl: string | null = null;

    Promise.all([getAuthorityAssessment(assessmentId), getAuthorityVideo(assessmentId)])
      .then(async ([detail, video]) => {
        if (!active) return;
        originalObjectUrl = URL.createObjectURL(video);
        if (detail.video.annotated_available) {
          const annotated = await getAuthorityAnnotatedVideo(assessmentId).catch(() => null);
          if (annotated && active) annotatedObjectUrl = URL.createObjectURL(annotated);
        }
        if (!active) return;
        setAssessment(detail);
        setRemarks(detail.shortlist.remarks ?? "");
        setVideoUrl(originalObjectUrl);
        setAnnotatedUrl(annotatedObjectUrl);
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError));
      });

    return () => {
      active = false;
      if (originalObjectUrl) URL.revokeObjectURL(originalObjectUrl);
      if (annotatedObjectUrl) URL.revokeObjectURL(annotatedObjectUrl);
    };
  }, [assessmentId]);

  async function shortlist() {
    if (!assessment) return;
    setSaving(true);
    setError("");
    try {
      const result = await shortlistAthlete(assessmentId, remarks);
      setAssessment({ ...assessment, shortlist: { shortlisted: true, shortlisted_at: result.shortlisted_at, remarks: result.remarks } });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function downloadReport() {
    setDownloadingReport(true);
    setError("");
    try {
      const { blob, filename } = await getAuthorityAssessmentReport(assessmentId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setDownloadingReport(false);
    }
  }

  if (error && !assessment) {
    return <StatePanel tone="error" icon="profile" title="Athlete assessment could not be loaded" description={error} actionLabel="Try again" onAction={() => window.location.reload()} />;
  }

  if (!assessment) return <AuthorityAssessmentSkeleton />;

  const { athlete, scores, recommendations } = assessment;

  return (
    <PageLayout>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="metric-label">Authority review</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight">{athlete.name}</h1>
          <p className="mt-2 text-muted-foreground">
            {athlete.sport} · {athlete.state} · Age {athlete.age} · {athlete.experience} years experience
          </p>
        </div>
        <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={downloadReport} disabled={downloadingReport}>
          {downloadingReport ? "Preparing PDF..." : "Download PDF Report"}
        </Button>
      </div>

      {error && <p className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-red-300">{error}</p>}

      <PageMainSection className="content-grid xl:grid-cols-2" label="Authority video review">
        <Card className="main-action-card">
          <CardHeader>
            <p className="metric-label">Source footage</p>
            <CardTitle>Uploaded video</CardTitle>
          </CardHeader>
          <CardContent>
            {videoUrl ? <video className="aspect-video max-h-[70vh] w-full max-w-full rounded-xl bg-black object-contain" controls playsInline src={videoUrl}><track kind="captions" /></video> : <StatePanel compact icon="video" title="Video unavailable" description="The original athlete video could not be retrieved." className="aspect-video" />}
          </CardContent>
        </Card>
        <Card className="main-action-card">
          <CardHeader>
            <p className="metric-label">Pose visualization</p>
            <CardTitle>Annotated skeleton video</CardTitle>
          </CardHeader>
          <CardContent>
            {annotatedUrl ? <video className="aspect-video max-h-[70vh] w-full max-w-full rounded-xl bg-black object-contain" controls playsInline src={annotatedUrl}><track kind="captions" /></video> : <StatePanel compact icon="activity" title="Annotated preview unavailable" description="This assessment does not include a generated skeleton video." className="aspect-video" />}
          </CardContent>
        </Card>
      </PageMainSection>

      <PageSupportingSection className="content-grid sm:grid-cols-2 xl:grid-cols-4" label="Authority score summary">
        {[
          ["Technique", scores.technique_score],
          ["Efficiency", scores.efficiency_score],
          ["Balance", scores.balance_score],
          ["Overall", scores.overall_score],
        ].map(([label, value]) => (
          <Card className="supporting-card" key={label}>
            <CardContent className="p-6">
              <p className="metric-label">{label}</p>
              <p className="mt-3 text-4xl font-black text-primary">{value == null ? "—" : Number(value).toFixed(1)}</p>
            </CardContent>
          </Card>
        ))}
      </PageSupportingSection>

      <PageSupportingSection className="content-grid lg:grid-cols-3" label="Authority recommendations">
        {[
          ["Strengths", recommendations.strengths],
          ["Weaknesses", recommendations.weaknesses],
          ["Improvement suggestions", recommendations.improvement_suggestions],
        ].map(([title, items]) => (
          <Card className="supporting-card" key={title as string}>
            <CardHeader>
              <CardTitle>{title as string}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {(items as string[]).map((item) => <li key={item}>• {item}</li>)}
              </ul>
            </CardContent>
          </Card>
        ))}
      </PageSupportingSection>

      <Card className="main-action-card">
        <CardHeader>
          <p className="metric-label">Trial selection</p>
          <CardTitle>{assessment.shortlist.shortlisted ? "Athlete shortlisted" : "Shortlist athlete"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea className="min-h-28 w-full rounded-xl border border-white/[0.1] bg-white/[0.035] p-4 text-sm outline-none focus:border-primary/40" maxLength={1000} placeholder="Optional remarks for the trial panel" value={remarks} onChange={(event) => setRemarks(event.target.value)} />
          <Button type="button" className="w-full sm:w-auto" disabled={saving} onClick={shortlist}>
            {saving ? "Saving..." : assessment.shortlist.shortlisted ? "Update shortlist remarks" : "Shortlist Athlete"}
          </Button>
          {assessment.shortlist.shortlisted_at && <p className="text-xs text-muted-foreground">Shortlisted {new Date(assessment.shortlist.shortlisted_at).toLocaleString()}</p>}
        </CardContent>
      </Card>
    </PageLayout>
  );
}
