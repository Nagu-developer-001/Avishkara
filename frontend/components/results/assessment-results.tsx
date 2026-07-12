"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { PageHeader } from "@/components/dashboard/page-header";
import { PageLayout, PageSupportingSection } from "@/components/layout/page-layout";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { ResultsSkeleton } from "@/components/loading/page-skeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SportIcon } from "@/components/ui/sport-icon";
import { StatePanel } from "@/components/ui/state-panel";
import { getApiErrorMessage } from "@/lib/api-error";
import {
  getAnnotatedVideoUrl,
  getAssessment,
  getAssessmentReport,
  getLeaderboardAnnotatedVideoUrl,
  getLeaderboardAssessment,
  getLeaderboardAssessmentReport,
  getLeaderboardUploadedVideoUrl,
  getUploadedVideoUrl,
} from "@/services/assessments";
import {
  getCoachReplayTimeline,
  getLeaderboardCoachReplayTimeline,
  getLeaderboardStoredBiomechanics,
  getStoredBiomechanics,
} from "@/services/video-analysis";
import type { AssessmentDetail, MetricDeviation } from "@/types/assessment";
import type {
  BiomechanicalMetrics,
  CoachReplayFrame,
  CoachReplayTimeline,
  RunningBiomechanicsMetrics,
} from "@/types/analysis";

type AssessmentResultsProps = {
  uploadId: string;
  mode?: "athlete" | "leaderboard";
};
type MetricRow = { label: string; value: MetricDeviation };
type RunningMetricCard = { label: string; value: string; helper: string };
type GaitSegment = { start: number; width: number };
type VideoPanel = {
  eyebrow: string;
  title: string;
  source: string;
  icon: "video" | "activity";
  failed: boolean;
};
type ReplayPhaseSegment = {
  phase: string;
  start: number;
  width: number;
};

function formatMetric(value: number, unit: string) {
  const suffix = unit === "degrees" ? "Â°" : ` ${unit.replaceAll("_", " ")}`;
  return `${value.toFixed(2)}${suffix}`;
}

function scoreTone(score: number) {
  if (score >= 80) return "Excellent";
  if (score >= 65) return "Strong";
  if (score >= 50) return "Developing";
  return "Foundation";
}

function formatOptionalMetric(value: number | null, suffix = "") {
  if (value == null) return "â€”";
  return `${value.toFixed(value >= 100 ? 0 : 2)}${suffix}`;
}

function runningMetricCards(running: RunningBiomechanicsMetrics): RunningMetricCard[] {
  return [
    {
      label: "Cadence",
      value: formatOptionalMetric(running.cadence_spm, " spm"),
      helper: "Steps per minute from detected foot strikes.",
    },
    {
      label: "Contact time",
      value: formatOptionalMetric(running.contact_time_ms, " ms"),
      helper: "Estimated time foot stays on ground.",
    },
    {
      label: "Flight time",
      value: formatOptionalMetric(running.flight_time_ms, " ms"),
      helper: "Estimated airborne time between contacts.",
    },
    {
      label: "Duty factor",
      value: formatOptionalMetric(running.duty_factor_pct, "%"),
      helper: "Ground-contact share of the step cycle.",
    },
    {
      label: "Stride timing symmetry",
      value: formatOptionalMetric(running.stride_time_symmetry_pct, "%"),
      helper: "Lower difference means left/right rhythm is closer.",
    },
    {
      label: "Vertical oscillation",
      value: formatOptionalMetric(running.vertical_oscillation_ratio_pct, "%"),
      helper: "Up-down hip movement relative to leg length.",
    },
  ];
}

function runningFrameRange(running: RunningBiomechanicsMetrics) {
  const frames = [
    ...running.gait_events.left_foot_strikes,
    ...running.gait_events.left_toe_offs,
    ...running.gait_events.right_foot_strikes,
    ...running.gait_events.right_toe_offs,
  ];
  return Math.max(...frames, 1);
}

function buildGaitSegments(strikes: number[], toeOffs: number[], maxFrame: number): GaitSegment[] {
  return strikes.flatMap((strike) => {
    const toeOff = toeOffs.find((frame) => frame > strike);
    if (!toeOff) return [];
    const start = Math.min(100, Math.max(0, (strike / maxFrame) * 100));
    const end = Math.min(100, Math.max(start + 1, (toeOff / maxFrame) * 100));
    return [{ start, width: end - start }];
  });
}

function averageAngle(metric: { left: number; right: number }) {
  return (metric.left + metric.right) / 2;
}

function formatReplayAngle(metric: { left: number; right: number }) {
  return `L ${metric.left.toFixed(0)}° / R ${metric.right.toFixed(0)}°`;
}

function nearestReplayFrame(
  frames: CoachReplayFrame[],
  currentMs: number,
): CoachReplayFrame | null {
  if (!frames.length) return null;
  return frames.reduce((nearest, frame) => (
    Math.abs(frame.timestamp_ms - currentMs) < Math.abs(nearest.timestamp_ms - currentMs)
      ? frame
      : nearest
  ), frames[0]);
}

function replayPhaseSegments(frames: CoachReplayFrame[]): ReplayPhaseSegment[] {
  if (!frames.length) return [];
  const totalMs = Math.max(frames.at(-1)?.timestamp_ms ?? 1, 1);
  const segments: ReplayPhaseSegment[] = [];
  let start = frames[0];
  for (const frame of frames.slice(1)) {
    if (frame.movement_phase === start.movement_phase) continue;
    const end = frames[frames.indexOf(frame) - 1];
    segments.push({
      phase: start.movement_phase,
      start: (start.timestamp_ms / totalMs) * 100,
      width: Math.max(1, ((end.timestamp_ms - start.timestamp_ms) / totalMs) * 100),
    });
    start = frame;
  }
  const last = frames.at(-1) ?? start;
  segments.push({
    phase: start.movement_phase,
    start: (start.timestamp_ms / totalMs) * 100,
    width: Math.max(1, ((last.timestamp_ms - start.timestamp_ms) / totalMs) * 100),
  });
  return segments;
}

function coachSignal(frame: CoachReplayFrame, deviations: AssessmentDetail["scores"]["metric_deviations"]) {
  if (!deviations) return "Frame synced";
  const kneeTarget = averageAngle({
    left: deviations.knee_angle.left.target,
    right: deviations.knee_angle.right.target,
  });
  const hipTarget = averageAngle({
    left: deviations.hip_angle.left.target,
    right: deviations.hip_angle.right.target,
  });
  const elbowTarget = averageAngle({
    left: deviations.elbow_angle.left.target,
    right: deviations.elbow_angle.right.target,
  });
  const angleDeviation = Math.max(
    Math.abs(averageAngle(frame.knee_angle) - kneeTarget),
    Math.abs(averageAngle(frame.hip_angle) - hipTarget),
    Math.abs(averageAngle(frame.elbow_angle) - elbowTarget),
  );
  const strideDeviation = Math.abs(
    frame.stride_length.value - deviations.stride_length.target,
  );
  if (angleDeviation >= 25 || strideDeviation >= 0.18) return "Needs attention";
  if (angleDeviation >= 12 || strideDeviation >= 0.08) return "Watch closely";
  return "Stable frame";
}

export function AssessmentResults({ uploadId, mode = "athlete" }: AssessmentResultsProps) {
  const videoRefs = useRef<Array<HTMLVideoElement | null>>([]);
  const [assessment, setAssessment] = useState<AssessmentDetail | null>(null);
  const [videoFailed, setVideoFailed] = useState(false);
  const [annotatedFailed, setAnnotatedFailed] = useState(false);
  const [annotatedRequest, setAnnotatedRequest] = useState(0);
  const [biomechanics, setBiomechanics] = useState<BiomechanicalMetrics | null>(null);
  const [coachReplay, setCoachReplay] = useState<CoachReplayTimeline | null>(null);
  const [currentPlaybackMs, setCurrentPlaybackMs] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [error, setError] = useState("");
  const [downloadingReport, setDownloadingReport] = useState(false);

  function applyPlaybackRate(rate: number) {
    setPlaybackRate(rate);
    videoRefs.current.forEach((video) => {
      if (video) video.playbackRate = rate;
    });
  }

  function replayVideos() {
    videoRefs.current.forEach((video) => {
      if (!video) return;
      video.currentTime = 0;
      video.playbackRate = playbackRate;
      void video.play();
    });
    setCurrentPlaybackMs(0);
  }

  async function downloadReport() {
    setDownloadingReport(true);
    setError("");
    try {
      const { blob, filename } = mode === "leaderboard"
        ? await getLeaderboardAssessmentReport(uploadId)
        : await getAssessmentReport(uploadId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(getApiErrorMessage(downloadError));
    } finally {
      setDownloadingReport(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const detail = mode === "leaderboard"
          ? await getLeaderboardAssessment(uploadId)
          : await getAssessment(uploadId);
        if (!active) return;
        setAssessment(detail);

        try {
          const storedBiomechanics = mode === "leaderboard"
            ? await getLeaderboardStoredBiomechanics(uploadId)
            : await getStoredBiomechanics(uploadId);
          setBiomechanics(storedBiomechanics);
        } catch {
          setBiomechanics(null);
        }

        try {
          const replay = mode === "leaderboard"
            ? await getLeaderboardCoachReplayTimeline(uploadId)
            : await getCoachReplayTimeline(uploadId);
          setCoachReplay(replay);
        } catch {
          setCoachReplay(null);
        }
      } catch (loadError) {
        if (active) setError(getApiErrorMessage(loadError));
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [mode, uploadId]);

  useEffect(() => {
    setAnnotatedFailed(false);
    setVideoFailed(false);
    setCurrentPlaybackMs(0);
  }, [annotatedRequest, uploadId]);

  useEffect(() => {
    videoRefs.current.forEach((video) => {
      if (video) video.playbackRate = playbackRate;
    });
  }, [playbackRate]);

  const metrics = useMemo<MetricRow[]>(() => {
    const deviations = assessment?.scores.metric_deviations;
    if (!deviations) return [];
    return [
      { label: "Left knee angle", value: deviations.knee_angle.left },
      { label: "Right knee angle", value: deviations.knee_angle.right },
      { label: "Left elbow angle", value: deviations.elbow_angle.left },
      { label: "Right elbow angle", value: deviations.elbow_angle.right },
      { label: "Left hip angle", value: deviations.hip_angle.left },
      { label: "Right hip angle", value: deviations.hip_angle.right },
      { label: "Stride length", value: deviations.stride_length },
    ];
  }, [assessment]);

  const videoUrl = useMemo(
    () => mode === "leaderboard"
      ? getLeaderboardUploadedVideoUrl(uploadId)
      : getUploadedVideoUrl(uploadId),
    [mode, uploadId],
  );
  const annotatedVideoUrl = useMemo(
    () => mode === "leaderboard"
      ? getLeaderboardAnnotatedVideoUrl(uploadId)
      : getAnnotatedVideoUrl(uploadId),
    [annotatedRequest, mode, uploadId],
  );
  const videoPanels = useMemo<VideoPanel[]>(() => [
    {
      eyebrow: "Source footage",
      title: "Original movement",
      source: videoUrl,
      icon: "video",
      failed: videoFailed,
    },
    {
      eyebrow: "Biomechanical overlay",
      title: "Annotated analysis",
      source: annotatedVideoUrl,
      icon: "activity",
      failed: annotatedFailed,
    },
  ], [annotatedFailed, annotatedVideoUrl, videoFailed, videoUrl]);
  const currentReplayFrame = useMemo(
    () => nearestReplayFrame(coachReplay?.frames ?? [], currentPlaybackMs),
    [coachReplay, currentPlaybackMs],
  );
  const replaySegments = useMemo(
    () => replayPhaseSegments(coachReplay?.frames ?? []),
    [coachReplay],
  );

  if (error) return <StatePanel tone="error" icon="activity" title="Assessment results could not be opened" description={error} actionLabel="Try again" onAction={() => window.location.reload()} />;
  if (!assessment) return <ResultsSkeleton />;

  const scores = assessment.scores;
  const recommendations = assessment.recommendations;
  const running = biomechanics?.running ?? null;
  const hasReliableRunningGait = Boolean(
    running
      && running.step_count >= 6
      && running.stride_analysis.foot_strikes.length >= 6
      && running.stride_analysis.step_intervals.length >= 5,
  );
  const scoreCards = [
    ["Technique", scores.technique_score],
    ["Efficiency", scores.efficiency_score],
    ["Balance", scores.balance_score],
  ] as const;
  const recommendationCards = [
    ["Strengths", "What is working well", recommendations.strengths, "check"],
    ["Weaknesses", "Where performance drops", recommendations.weaknesses, "pulse"],
    ["Improvement suggestions", "Your next training focus", recommendations.improvement_suggestions, "arrow"],
  ] as const;

  return (
    <PageLayout>
      <PageHeader
        eyebrow="Completed assessment"
        title={assessment.video.filename}
        description={`${assessment.video.sport} Â· ${new Date(assessment.video.upload_time).toLocaleString()}`}
        action={
          <div className="flex w-full flex-col-reverse gap-3 sm:w-auto sm:flex-row sm:items-center">
            <Button className="w-full sm:w-auto" type="button" variant="outline" onClick={downloadReport} disabled={downloadingReport}>
              {downloadingReport ? "Preparing PDFâ€¦" : "Download PDF Report"}
            </Button>
            <span className="inline-flex items-center justify-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-2 text-xs font-bold text-primary">
              <SportIcon name="check" className="h-4 w-4" /> ANALYSIS COMPLETE
            </span>
          </div>
        }
      />

      <section className="content-grid lg:grid-cols-[1.2fr_2fr]" aria-label="Assessment score summary">
        <Card className="main-action-card group relative min-h-64 transition duration-300 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-[0_24px_80px_hsl(var(--primary)/0.12)]">
          <div className="absolute -right-12 -top-16 h-52 w-52 rounded-full border-[34px] border-primary/[0.07] transition-transform duration-700 group-hover:scale-110" />
          <CardContent className="relative flex h-full min-h-64 flex-col justify-between p-6 sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <div><p className="metric-label">Composite performance</p><h2 className="mt-2 text-xl font-bold">Overall score</h2></div>
              <span className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-bold text-primary">{scoreTone(scores.overall_score ?? 0)}</span>
            </div>
            <div>
              <p className="text-7xl font-black tracking-[-0.08em] text-primary sm:text-8xl">{scores.overall_score == null ? "â€”" : <AnimatedNumber value={scores.overall_score} />}<span className="ml-2 text-base font-bold tracking-normal text-muted-foreground">/100</span></p>
              <p className="mt-3 max-w-sm text-xs leading-5 text-muted-foreground">Weighted across technique, efficiency and bilateral balance.</p>
            </div>
          </CardContent>
        </Card>

        <Card className="supporting-card">
          <CardHeader className="section-card-header"><p className="metric-label">Performance indices</p><CardTitle>Score breakdown</CardTitle></CardHeader>
          <CardContent className="grid gap-3 p-4 sm:grid-cols-3 sm:p-6">
            {scoreCards.map(([label, value], index) => (
              <div key={label} className="group rounded-2xl border border-border/70 bg-background/25 p-5 transition duration-300 hover:-translate-y-1 hover:border-primary/30 hover:bg-primary/[0.04]">
                <div className="flex items-start justify-between"><p className="metric-label">{label}</p><span className="text-[0.65rem] font-bold text-muted-foreground">0{index + 1}</span></div>
                <p className="mt-6 text-4xl font-black tracking-tight"><AnimatedNumber value={Number(value)} decimals={1} /></p>
                <p className="mt-1 text-xs font-semibold text-primary">{scoreTone(Number(value))}</p>
                <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-muted"><div className="score-fill h-full rounded-full bg-gradient-to-r from-primary to-accent" style={{ width: `${Math.min(100, Number(value))}%`, animationDelay: `${index * 100}ms` }} /></div>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <PageSupportingSection className="content-grid xl:grid-cols-2" label="Video comparison">
        {videoPanels.map(({ eyebrow, title, source, icon, failed }, index) => (
          <Card key={title} className={`supporting-card group transition duration-300 ${index ? "border-accent/20 hover:border-accent/40" : "hover:border-primary/25"}`}>
            <CardHeader className="section-card-header">
              <div className="flex items-center gap-3"><span className={`grid h-10 w-10 place-items-center rounded-xl ${index ? "bg-accent/10 text-accent" : "bg-muted text-muted-foreground"}`}><SportIcon name={icon} className="h-5 w-5" /></span><div><p className="metric-label">{eyebrow}</p><CardTitle>{title}</CardTitle></div></div>
            </CardHeader>
            <CardContent className="p-3 sm:p-5">
              {source && !failed ? (
                <video
                  key={`${title}-${annotatedRequest}`}
                  ref={(node) => {
                    videoRefs.current[index] = node;
                    if (node) node.playbackRate = playbackRate;
                  }}
                  className="aspect-video max-h-[70vh] w-full max-w-full rounded-xl border border-border bg-black object-contain shadow-2xl"
                  autoPlay
                  controls
                  muted
                  playsInline
                  preload="auto"
                  src={source as string}
                  onLoadedMetadata={(event) => {
                    event.currentTarget.playbackRate = playbackRate;
                  }}
                  onSeeked={(event) => setCurrentPlaybackMs(event.currentTarget.currentTime * 1000)}
                  onTimeUpdate={(event) => setCurrentPlaybackMs(event.currentTarget.currentTime * 1000)}
                  onError={() => index ? setAnnotatedFailed(true) : setVideoFailed(true)}
                >
                  <track kind="captions" />
                </video>
              ) : (
                <StatePanel compact icon="video" title="Video unavailable" description={index ? "The annotated preview could not be played. The analysis results are still available below." : "The original video could not be played."} actionLabel={index ? "Retry preview" : undefined} onAction={index ? () => setAnnotatedRequest((request) => request + 1) : undefined} className="aspect-video" />
              )}
            </CardContent>
          </Card>
        ))}
      </PageSupportingSection>

      {currentReplayFrame && coachReplay && (
        <Card className="supporting-card border-primary/25 bg-gradient-to-br from-card via-card to-primary/[0.04]">
          <CardHeader className="section-card-header">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="metric-label">Coach replay mode</p>
                <CardTitle>Frame-synced biomechanics</CardTitle>
                <p className="mt-2 text-sm text-muted-foreground">
                  Play or scrub the video above to watch metrics change with the current frame.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button type="button" size="sm" variant="outline" onClick={replayVideos}>
                  Replay
                </Button>
                {[0.25, 0.5, 1].map((rate) => (
                  <Button
                    key={rate}
                    type="button"
                    size="sm"
                    variant={playbackRate === rate ? "default" : "outline"}
                    onClick={() => applyPlaybackRate(rate)}
                  >
                    {rate}x
                  </Button>
                ))}
                <span className="inline-flex w-fit items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-black text-primary">
                  <SportIcon name="activity" className="h-4 w-4" />
                  {coachSignal(currentReplayFrame, assessment.scores.metric_deviations)}
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5 p-4 sm:p-6">
            <div className="grid gap-3 lg:grid-cols-[1fr_1.4fr]">
              <div className="rounded-2xl border border-border/70 bg-background/25 p-5">
                <p className="metric-label">Current moment</p>
                <div className="mt-4 flex flex-wrap items-end gap-4">
                  <div>
                    <p className="text-4xl font-black text-primary">
                      {(currentReplayFrame.timestamp_ms / 1000).toFixed(2)}s
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Frame {currentReplayFrame.frame_index}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-accent/20 bg-accent/10 px-4 py-3">
                    <p className="metric-label">Phase</p>
                    <p className="mt-1 text-lg font-black text-accent">
                      {currentReplayFrame.movement_phase}
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  ["Knee angle", formatReplayAngle(currentReplayFrame.knee_angle), "Lower-body loading"],
                  ["Hip angle", formatReplayAngle(currentReplayFrame.hip_angle), "Posture and extension"],
                  ["Elbow angle", formatReplayAngle(currentReplayFrame.elbow_angle), "Arm mechanics"],
                  [
                    "Stride length",
                    `${currentReplayFrame.stride_length.value.toFixed(3)} ${currentReplayFrame.stride_length.unit.replaceAll("_", " ")}`,
                    "Step separation",
                  ],
                ].map(([label, value, helper]) => (
                  <div
                    key={label}
                    className="rounded-2xl border border-border/70 bg-background/25 p-4 transition duration-300 hover:-translate-y-0.5 hover:border-primary/30"
                  >
                    <p className="metric-label">{label}</p>
                    <p className="mt-3 text-xl font-black tracking-tight">{value}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{helper}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-border/70 bg-background/20 p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="metric-label">Replay timeline</p>
                  <h3 className="mt-1 text-lg font-black">Current phase tracker</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  {coachReplay.processed_frames} processed frames from {coachReplay.total_frames} video frames.
                </p>
              </div>
              <div className="relative mt-5 h-10 overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.035]">
                {replaySegments.map((segment, index) => (
                  <span
                    key={`${segment.phase}-${index}`}
                    title={segment.phase}
                    className={`absolute inset-y-0 border-r border-background/40 ${
                      segment.phase === currentReplayFrame.movement_phase
                        ? "bg-primary/45"
                        : "bg-accent/20"
                    }`}
                    style={{ left: `${segment.start}%`, width: `${segment.width}%` }}
                  />
                ))}
                <span
                  className="absolute inset-y-0 w-1 rounded-full bg-white shadow-[0_0_24px_hsl(var(--primary))]"
                  style={{
                    left: `${Math.min(
                      99,
                      Math.max(
                        0,
                        (currentReplayFrame.timestamp_ms / Math.max(coachReplay.frames.at(-1)?.timestamp_ms ?? 1, 1)) * 100,
                      ),
                    )}%`,
                  }}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {[...new Set(coachReplay.frames.map((frame) => frame.movement_phase))].map((phase) => (
                  <span
                    key={phase}
                    className={`rounded-full border px-3 py-1.5 text-xs font-bold ${
                      phase === currentReplayFrame.movement_phase
                        ? "border-primary/30 bg-primary/10 text-primary"
                        : "border-border/70 bg-background/30 text-muted-foreground"
                    }`}
                  >
                    {phase}
                  </span>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {scores.phase_scores.length > 0 && (
        <Card className="supporting-card">
          <CardHeader className="section-card-header"><p className="metric-label">Temporal intelligence</p><CardTitle>Movement phases</CardTitle></CardHeader>
          <CardContent className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3 sm:p-6">
            {scores.phase_scores.map((phase, index) => (
              <div key={phase.movement_phase} className="group rounded-2xl border border-border/70 bg-background/20 p-5 transition duration-300 hover:-translate-y-1 hover:border-accent/30">
                <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold text-primary">PHASE {String(index + 1).padStart(2, "0")}</p><p className="mt-2 font-bold">{phase.movement_phase}</p><p className="mt-1 text-xs text-muted-foreground">Frames {phase.start_frame}â€“{phase.end_frame}</p></div><p className="text-3xl font-black text-accent"><AnimatedNumber value={phase.overall_score} /></p></div>
                <dl className="mt-5 grid grid-cols-3 gap-2 border-t border-border/70 pt-4 text-xs">
                  <div><dt className="text-muted-foreground">Technique</dt><dd className="mt-1 font-bold"><AnimatedNumber value={phase.technique_score} decimals={1} /></dd></div>
                  <div><dt className="text-muted-foreground">Efficiency</dt><dd className="mt-1 font-bold"><AnimatedNumber value={phase.efficiency_score} decimals={1} /></dd></div>
                  <div><dt className="text-muted-foreground">Balance</dt><dd className="mt-1 font-bold"><AnimatedNumber value={phase.balance_score} decimals={1} /></dd></div>
                </dl>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {running && (
        <Card className="supporting-card border-accent/20 bg-gradient-to-br from-card via-card to-accent/[0.035]">
          <CardHeader className="section-card-header">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="metric-label">Running gait intelligence</p>
                <CardTitle>Stride, contact and rhythm metrics</CardTitle>
              </div>
              <span className="inline-flex w-fit items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-3 py-1.5 text-xs font-bold text-accent">
                <SportIcon name="activity" className="h-4 w-4" />
                {hasReliableRunningGait ? `${running.step_count} detected steps` : "Gait events not reliable"}
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-5 p-4 sm:p-6">
            {!hasReliableRunningGait ? (
              <div role="alert" className="rounded-2xl border border-amber-400/35 bg-amber-400/[0.09] p-5 shadow-[0_18px_55px_rgba(251,191,36,0.08)]">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-amber-400/35 bg-amber-400/15 text-amber-300">
                    <SportIcon name="activity" className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-black uppercase tracking-[0.2em] text-amber-300">Stride warning</p>
                    <h3 className="mt-2 text-xl font-black tracking-[-0.03em]">Gait timeline could not be trusted for this video</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      Avishkara did not show detected foot landings, stance vs swing, or stride intervals because the system could not detect enough reliable alternating foot strikes. Showing those charts would be misleading.
                    </p>
                    <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
                      <div className="rounded-xl border border-amber-400/20 bg-background/30 p-4">
                        <p className="font-black text-foreground">Likely causes</p>
                        <ul className="mt-2 space-y-1 text-muted-foreground">
                          <li>• Movement is walking or too slow for running gait.</li>
                          <li>• Feet are partly hidden or blurred.</li>
                          <li>• Camera angle is not clean side-view.</li>
                        </ul>
                      </div>
                      <div className="rounded-xl border border-amber-400/20 bg-background/30 p-4">
                        <p className="font-black text-foreground">Record again with</p>
                        <ul className="mt-2 space-y-1 text-muted-foreground">
                          <li>• Full body visible from head to feet.</li>
                          <li>• Side-view camera at hip height.</li>
                          <li>• Clear running cycle with multiple steps.</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {runningMetricCards(running).map((metric, index) => (
                    <div
                      key={metric.label}
                      className="group rounded-2xl border border-border/70 bg-background/25 p-5 transition duration-300 hover:-translate-y-1 hover:border-accent/35 hover:bg-accent/[0.045]"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="metric-label">{metric.label}</p>
                        <span className="text-[0.65rem] font-bold text-muted-foreground">
                          R{String(index + 1).padStart(2, "0")}
                        </span>
                      </div>
                      <p className="mt-5 text-3xl font-black tracking-tight text-accent">{metric.value}</p>
                      <p className="mt-2 text-xs leading-5 text-muted-foreground">{metric.helper}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-3 rounded-2xl border border-border/70 bg-background/20 p-4 text-sm md:grid-cols-4">
                  {[
                    ["Left strikes", running.gait_events.left_foot_strikes.length],
                    ["Right strikes", running.gait_events.right_foot_strikes.length],
                    ["Left toe-offs", running.gait_events.left_toe_offs.length],
                    ["Right toe-offs", running.gait_events.right_toe_offs.length],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-4">
                      <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
                      <p className="mt-2 text-2xl font-black text-primary">{value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-2xl border border-border/70 bg-background/20 p-5">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="metric-label">Gait cycle timeline</p>
                    <h3 className="mt-1 text-lg font-black">Stance vs swing</h3>
                  </div>
                  <p className="text-xs text-muted-foreground">Colored bars show estimated ground contact.</p>
                </div>
                {(["left", "right"] as const).map((side) => {
                  const maxFrame = runningFrameRange(running);
                  const strikes = side === "left" ? running.gait_events.left_foot_strikes : running.gait_events.right_foot_strikes;
                  const toeOffs = side === "left" ? running.gait_events.left_toe_offs : running.gait_events.right_toe_offs;
                  const segments = buildGaitSegments(strikes, toeOffs, maxFrame);

                  return (
                    <div key={side} className="mt-5 grid grid-cols-[3.5rem_1fr] items-center gap-3">
                      <p className="text-xs font-black uppercase tracking-wider text-muted-foreground">{side}</p>
                      <div className="relative h-7 overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.035]">
                        <div className="absolute inset-y-0 left-1/2 w-px bg-border/80" />
                        {segments.map((segment, index) => (
                          <span
                            key={`${side}-${index}-${segment.start}`}
                            className="absolute inset-y-1 rounded-md bg-accent/75 shadow-[0_0_18px_hsl(var(--accent)/0.25)]"
                            style={{ left: `${segment.start}%`, width: `${segment.width}%` }}
                          />
                        ))}
                      </div>
                    </div>
                  );
                })}
                <div className="mt-5 flex flex-wrap gap-4 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-2"><i className="h-2.5 w-2.5 rounded-sm bg-accent" /> Stance/contact</span>
                  <span className="inline-flex items-center gap-2"><i className="h-2.5 w-2.5 rounded-sm bg-white/[0.12]" /> Swing/flight</span>
                </div>
              </div>

              <div className="rounded-2xl border border-border/70 bg-background/20 p-5">
                <div>
                  <p className="metric-label">Stride footprint map</p>
                  <h3 className="mt-1 text-lg font-black">Detected foot landings</h3>
                  <p className="mt-1 text-xs text-muted-foreground">Markers show foot-strike order across time; raw pose coordinates stay in the tooltip.</p>
                </div>
                <div className="relative mt-6 h-32 overflow-hidden rounded-2xl border border-white/[0.06] bg-[linear-gradient(90deg,transparent_0,transparent_24px,hsl(var(--border)/0.35)_25px),linear-gradient(180deg,transparent_0,transparent_24px,hsl(var(--border)/0.24)_25px)] bg-[length:26px_26px]">
                  <div className="absolute left-5 right-5 top-1/2 h-px bg-gradient-to-r from-transparent via-muted-foreground/40 to-transparent" />
                  {running.stride_analysis.foot_strikes.map((marker, index) => (
                    <span
                      key={`${marker.side}-${marker.frame_index}-${index}`}
                      title={`${marker.side} foot strike · frame ${marker.frame_index} · x ${marker.foot_x.toFixed(2)} · y ${marker.foot_y.toFixed(2)}`}
                      className={`absolute grid h-7 w-7 -translate-x-1/2 place-items-center rounded-full border text-[0.65rem] font-black shadow-lg ${
                        marker.side === "left"
                          ? "top-8 border-accent/40 bg-accent/20 text-accent"
                          : "bottom-8 border-primary/40 bg-primary/20 text-primary"
                      }`}
                      style={{ left: `${Math.min(96, Math.max(4, (marker.frame_index / runningFrameRange(running)) * 100))}%` }}
                    >
                      {marker.side === "left" ? "L" : "R"}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {running.stride_analysis.stride_intervals.length > 0 && (
              <div className="rounded-2xl border border-border/70 bg-background/20 p-5">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="metric-label">Stride intervals</p>
                    <h3 className="mt-1 text-lg font-black">Same-foot stride measurements</h3>
                  </div>
                  <p className="text-xs text-muted-foreground">Distance is normalized by estimated leg length.</p>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {running.stride_analysis.stride_intervals.slice(0, 8).map((interval, index) => (
                    <div key={`${interval.side}-${interval.start_frame}-${interval.end_frame}`} className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-black uppercase tracking-wider text-muted-foreground">
                          {interval.side} stride {index + 1}
                        </p>
                        <span className="rounded-full border border-accent/20 bg-accent/10 px-2 py-0.5 text-[0.65rem] font-bold text-accent">
                          {interval.start_frame}-{interval.end_frame}
                        </span>
                      </div>
                      <p className="mt-3 text-2xl font-black text-foreground">
                        {interval.stride_length_norm == null ? "â€”" : interval.stride_length_norm.toFixed(2)}
                        <span className="ml-1 text-xs text-muted-foreground">leg lengths</span>
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">{interval.duration_ms.toFixed(0)} ms</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="supporting-card">
        <CardHeader className="section-card-header"><p className="metric-label">Explainable comparison</p><CardTitle>Biomechanical metrics</CardTitle></CardHeader>
        <CardContent className="p-0">
          {metrics.length ? (
            <div className="overflow-x-auto px-4 pb-2 sm:px-6">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground"><tr><th className="py-4">Metric</th><th>Measured</th><th>Benchmark</th><th>Deviation</th></tr></thead>
                <tbody>{metrics.map(({ label, value }) => <tr key={label} className="border-b border-border/60 last:border-0 transition hover:bg-primary/[0.035]"><td className="py-4 font-bold">{label}</td><td className="font-semibold text-accent">{formatMetric(value.actual, value.unit)}</td><td>{formatMetric(value.target, value.unit)}</td><td className={Math.abs(value.signed_deviation) > 10 ? "text-primary" : "text-muted-foreground"}>{formatMetric(value.signed_deviation, value.unit)}</td></tr>)}</tbody>
              </table>
            </div>
          ) : <StatePanel compact icon="pulse" title="Metrics unavailable" description="Detailed biomechanical measurements were not stored for this assessment." className="m-5" />}
        </CardContent>
      </Card>

      <section className="content-grid lg:grid-cols-3" aria-label="Assessment recommendations">
        {recommendationCards.map(([title, subtitle, items, icon], index) => (
          <Card key={title} className="supporting-card group transition duration-300 hover:-translate-y-1 hover:border-primary/25">
            <CardHeader className="section-card-header"><div className="flex items-center gap-3"><span className={`grid h-10 w-10 place-items-center rounded-xl ${index === 0 ? "bg-accent/10 text-accent" : index === 1 ? "bg-primary/10 text-primary" : "bg-muted text-foreground"}`}><SportIcon name={icon as "check" | "pulse" | "arrow"} className="h-5 w-5" /></span><div><CardTitle className="text-lg">{title}</CardTitle><p className="mt-1 text-xs text-muted-foreground">{subtitle}</p></div></div></CardHeader>
            <CardContent className="p-5">
              {items.length ? (
                <ul className="space-y-3 text-sm leading-6">{items.map((item) => <li key={item} className="flex gap-3"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" /><span>{item}</span></li>)}</ul>
              ) : (
                <StatePanel compact icon={icon as "check" | "pulse" | "arrow"} title={`No ${title.toLowerCase()} recorded`} description="The assessment completed successfully, but this category did not produce a separate rule-based note." />
              )}
            </CardContent>
          </Card>
        ))}
      </section>
    </PageLayout>
  );
}


