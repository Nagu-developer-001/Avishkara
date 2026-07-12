"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type DragEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import MagicRings from "@/components/ui/magic-rings";
import { Progress } from "@/components/ui/progress";
import { SportIcon } from "@/components/ui/sport-icon";
import { ACCEPTED_VIDEO_EXTENSIONS, SUPPORTED_SPORTS } from "@/constants/upload";
import { getApiErrorMessage } from "@/lib/api-error";
import { validateVideoFile } from "@/lib/file-validation";
import { cn } from "@/lib/utils";
import { analyzeVideo } from "@/services/video-analysis";
import { uploadVideo } from "@/services/video-upload";
import type { AnalysisStage } from "@/types/analysis";
import type { Sport, UploadStatus } from "@/types/upload";

const WORKFLOW_STAGES = [
  { key: "uploading", label: "Uploading", detail: "Securely sending footage" },
  { key: "processing-video", label: "Processing video", detail: "Reading frames and metadata" },
  { key: "extracting-pose", label: "Extracting pose", detail: "Detecting 33 body landmarks" },
  { key: "calculating-biomechanics", label: "Calculating biomechanics", detail: "Measuring angles, stride and rhythm" },
  { key: "comparing-benchmarks", label: "Comparing benchmarks", detail: "Scoring against the sport profile" },
  { key: "generating-assessment", label: "Generating assessment", detail: "Saving results and recommendations" },
  { key: "completed", label: "Completed", detail: "Opening the analysis report" },
] as const;

function formatFileSize(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function sportLabel(value: Sport | "") {
  if (value === "Bowling") return "Cricket Bowling";
  return value || "Sport not selected";
}

function statusCopy(status: UploadStatus, analysisStage: AnalysisStage | null, progress: number) {
  if (status === "idle") return { label: "Waiting for footage", detail: "Choose a sport and add a clear full-body performance video." };
  if (status === "ready") return { label: "Ready for upload", detail: "Validation passed. Send the file to begin the analysis pipeline." };
  if (status === "uploading") return { label: `Uploading ${progress}%`, detail: "Keep this page open while the video is transferred." };
  if (status === "complete" && !analysisStage) return { label: "Upload complete", detail: "Start analysis to extract pose, biomechanics, benchmarks, and results." };
  if (status === "analyzing") {
    const stage = WORKFLOW_STAGES.find((item) => item.key === analysisStage);
    return { label: stage?.label ?? "Preparing analysis", detail: stage?.detail ?? "The sports analysis console is warming up." };
  }
  return { label: "Analysis complete", detail: "Redirecting to results." };
}

export function VideoUploader() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sport, setSport] = useState<Sport | "">("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [analysisStage, setAnalysisStage] = useState<AnalysisStage | null>(null);

  function selectFile(selectedFile: File | undefined) {
    if (!selectedFile) return;

    const validation = validateVideoFile(selectedFile);
    if (!validation.valid) {
      setFile(null);
      setError(validation.message);
      setStatus("idle");
      setProgress(0);
      return;
    }

    setFile(selectedFile);
    setError(null);
    setSuccess(null);
    setProgress(0);
    setStatus("ready");
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  function clearSelection() {
    setFile(null);
    setSport("");
    setError(null);
    setSuccess(null);
    setProgress(0);
    setStatus("idle");
    setUploadId(null);
    setAnalysisStage(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function startUpload() {
    if (!file || !sport) return;
    setError(null);
    setSuccess(null);
    setProgress(0);
    setStatus("uploading");

    try {
      const result = await uploadVideo(file, sport, setProgress);
      setProgress(100);
      setStatus("complete");
      setUploadId(result.upload_id);
      setSuccess("Footage uploaded. Analysis console is ready.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
      setStatus("ready");
      setProgress(0);
    }
  }

  async function startAnalysis() {
    if (!uploadId) return;
    setError(null);
    setSuccess(null);
    setStatus("analyzing");

    try {
      await analyzeVideo(uploadId, setAnalysisStage);
      window.dispatchEvent(new CustomEvent("assessment-completed"));
      setTimeout(() => {
        router.push(`/dashboard/results/${uploadId}`);
        router.refresh();
      }, 400);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
      setStatus("complete");
      setAnalysisStage(null);
    }
  }

  const isUploading = status === "uploading";
  const isAnalyzing = status === "analyzing";
  const isBusy = isUploading || isAnalyzing;
  const activeStageIndex = analysisStage ? WORKFLOW_STAGES.findIndex((stage) => stage.key === analysisStage) : 0;
  const safeActiveStageIndex = Math.max(activeStageIndex, 0);
  const currentStatus = statusCopy(status, analysisStage, progress);

  return (
    <div className="relative isolate overflow-hidden rounded-[1.5rem]">
      <Card className={cn("main-action-card relative z-10 backdrop-blur-sm", isAnalyzing && "cursor-wait")}>
        {isAnalyzing && (
          <div
            aria-hidden="true"
            className="absolute inset-0 z-20 rounded-[1.5rem] bg-background/[0.42] backdrop-blur-[1px]"
          />
        )}
        <CardHeader className="section-card-header">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle className="flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-xl border border-primary/20 bg-primary/10 text-primary shadow-[0_0_32px_hsl(var(--primary)/0.12)]">
                  <SportIcon name="video" className="h-5 w-5" />
                </span>
                Sports analysis console
              </CardTitle>
              <CardDescription className="mt-2">MP4, MOV, or WebM · maximum 200 MB · full-body footage recommended</CardDescription>
            </div>
            <div className="rounded-2xl border border-primary/20 bg-primary/[0.075] px-4 py-3">
              <p className="metric-label">Console status</p>
              <p className="mt-1 text-sm font-black text-primary">{currentStatus.label}</p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6 p-6 lg:p-8">
          <div
            onDragEnter={(event) => {
              event.preventDefault();
              if (!isBusy) setIsDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              const nextTarget = event.relatedTarget;
              if (!nextTarget || !event.currentTarget.contains(nextTarget as Node)) {
                setIsDragging(false);
              }
            }}
            onDrop={handleDrop}
            className={cn(
              "group relative flex min-h-80 flex-col items-center justify-center overflow-hidden rounded-[1.35rem] border border-dashed px-6 text-center transition-all duration-300",
              isDragging
                ? "scale-[1.01] border-primary bg-primary/10 shadow-[0_0_70px_hsl(var(--primary)/0.2)]"
                : "border-primary/25 bg-card/[0.42] hover:border-primary/45 hover:bg-primary/[0.045]",
              isBusy && "pointer-events-none opacity-70",
            )}
          >
            <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,transparent,hsl(var(--primary)/0.08),transparent)] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            <div className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/70 to-transparent" />
            <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-primary/[0.08] to-transparent" />

            <span className="mb-5 grid h-20 w-20 place-items-center rounded-[1.4rem] border border-primary/25 bg-primary/10 text-primary shadow-[0_0_42px_hsl(var(--primary)/0.16)] transition-transform duration-300 group-hover:-translate-y-1 group-hover:scale-105">
              <SportIcon name="upload" className="h-8 w-8" />
            </span>
            <p className="text-xs font-black uppercase tracking-[0.26em] text-primary">Drop zone armed</p>
            <p className="mt-3 text-2xl font-black tracking-[-0.04em]">Drop performance footage here</p>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">Use a stable camera angle where the athlete is visible head-to-foot for the complete movement.</p>
            <div className="mt-5 flex flex-wrap justify-center gap-2 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-muted-foreground">
              <span className="rounded-full border border-border/70 bg-card/[0.5] px-3 py-1">Full body</span>
              <span className="rounded-full border border-border/70 bg-card/[0.5] px-3 py-1">Stable camera</span>
              <span className="rounded-full border border-border/70 bg-card/[0.5] px-3 py-1">One athlete</span>
            </div>
            <Button type="button" variant="outline" className="mt-5 w-full sm:w-auto" disabled={isBusy} onClick={() => inputRef.current?.click()}>
              Choose footage
            </Button>
            <input ref={inputRef} type="file" accept={ACCEPTED_VIDEO_EXTENSIONS} className="sr-only" disabled={isBusy} onChange={(event) => selectFile(event.target.files?.[0])} />
          </div>

          {error && (
            <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </p>
          )}

          <div className="rounded-2xl border border-accent/15 bg-accent/[0.04] px-4 py-4 text-sm text-muted-foreground">
            <p className="flex items-center gap-2 font-bold text-foreground">
              <SportIcon name="pulse" className="h-4 w-4 text-accent" /> Capture protocol
            </p>
            <ul className="mt-2 space-y-1">
              <li>• Keep the athlete visible from head to feet throughout the video.</li>
              <li>• Record the complete selected sports movement, not a close-up.</li>
              <li>• Use a stable camera with enough light and minimal obstruction.</li>
            </ul>
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <div className="space-y-2">
              <label htmlFor="sport" className="metric-label">
                Sport profile
              </label>
              <select
                id="sport"
                value={sport}
                disabled={isBusy || status === "complete"}
                onChange={(event) => setSport(event.target.value as Sport | "")}
                className="flex h-12 w-full rounded-xl border border-input bg-[#0b111b] px-4 py-2 text-sm font-semibold outline-none transition-all focus:border-primary/50 focus:ring-2 focus:ring-primary/15"
                required
              >
                <option value="">Select sport</option>
                {SUPPORTED_SPORTS.map((option) => (
                  <option key={option} value={option}>
                    {sportLabel(option)}
                  </option>
                ))}
              </select>
            </div>

            <div className="rounded-2xl border border-border/70 bg-card/[0.42] p-4">
              <p className="metric-label">Selected mode</p>
              <p className="mt-2 text-lg font-black text-foreground">{sportLabel(sport)}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{currentStatus.detail}</p>
            </div>
          </div>

          {file && (
            <div className="rounded-2xl border border-primary/20 bg-card/[0.48] p-4 shadow-[0_16px_50px_hsl(var(--primary)/0.07)]">
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 gap-4">
                  <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
                    <SportIcon name="video" className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="metric-label">Footage locked</p>
                    <p className="mt-1 truncate text-sm font-black">{file.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{formatFileSize(file.size)} · {sportLabel(sport)}</p>
                  </div>
                </div>
                {!isBusy && status !== "complete" && (
                  <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={clearSelection}>
                    Remove
                  </Button>
                )}
              </div>

              {(isUploading || status === "complete") && (
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-xs font-bold text-muted-foreground">
                    <span>{status === "complete" ? "Transfer complete" : "Transfer in progress"}</span>
                    <span className="text-primary">{progress}%</span>
                  </div>
                  <Progress value={progress} aria-label={`Upload progress: ${progress}%`} />
                </div>
              )}
            </div>
          )}

          {success && (
            <p role="status" className="rounded-xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm text-primary">
              {success}
            </p>
          )}

          {(isUploading || status === "complete" || isAnalyzing) && (
            <div className={cn("relative overflow-hidden rounded-2xl border border-primary/20 bg-card/[0.48] p-4", isAnalyzing && "z-30 border-primary/35 bg-card/[0.74] shadow-[0_0_70px_hsl(var(--primary)/0.16)]")}>
              {isAnalyzing && (
                <>
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-px animate-pulse bg-gradient-to-r from-transparent via-primary to-transparent" />
                  <div className="pointer-events-none absolute -right-10 -top-24 z-10 h-[22rem] w-[22rem] opacity-95 mix-blend-screen [mask-image:radial-gradient(circle_at_center,black,transparent_76%)] sm:h-[26rem] sm:w-[26rem]">
                    <MagicRings
                      color="#00D4FF"
                      colorTwo="#A855F7"
                      ringCount={8}
                      speed={1.25}
                      attenuation={8}
                      lineThickness={2.4}
                      baseRadius={0.28}
                      radiusStep={0.085}
                      scaleRate={0.14}
                      opacity={0.95}
                      blur={0.2}
                      noiseAmount={0.1}
                      rotation={-12}
                      ringGap={1.42}
                      fadeIn={0.7}
                      fadeOut={0.5}
                      followMouse={false}
                      mouseInfluence={0.2}
                      hoverScale={1.2}
                      parallax={0.05}
                      clickBurst={false}
                    />
                  </div>
                  <div className="pointer-events-none absolute inset-0 z-20 bg-[radial-gradient(circle_at_78%_16%,transparent_0,hsl(var(--card)/0.18)_34%,hsl(var(--card)/0.74)_76%)]" />
                </>
              )}
              <div className="relative z-30 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="metric-label">Analysis pipeline</p>
                  <h3 className="mt-1 text-xl font-black tracking-[-0.03em]">{currentStatus.label}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{currentStatus.detail}</p>
                </div>
                <span className="w-fit rounded-full border border-primary/25 bg-primary/10 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-primary">
                  {isAnalyzing ? "Live analysis" : status === "complete" ? "Ready" : "Transfer"}
                </span>
              </div>
              <ol className="relative z-30 mt-5 grid gap-3 sm:grid-cols-2">
                {WORKFLOW_STAGES.map((stage, index) => {
                  const isActive = isUploading ? index === 0 : isAnalyzing && index === safeActiveStageIndex;
                  const isComplete = isUploading ? false : analysisStage === "completed" || index < safeActiveStageIndex || (index === 0 && !analysisStage);

                  return (
                    <li
                      key={stage.key}
                      className={cn(
                        "relative overflow-hidden rounded-xl border border-border/70 bg-card/[0.42] px-3 py-3 text-xs text-muted-foreground transition-all duration-300",
                        isActive && "scale-[1.01] border-accent/40 bg-accent/10 text-accent shadow-[0_0_34px_hsl(var(--accent)/0.12)]",
                        isComplete && "border-primary/25 bg-primary/10 text-primary",
                      )}
                    >
                      {isActive && <span className="absolute inset-y-0 left-0 w-1 animate-pulse bg-accent" />}
                      <div className="flex items-start gap-3">
                        <span className={cn("mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border text-[0.65rem] font-black", isComplete ? "border-primary/30 bg-primary/15" : isActive ? "border-accent/40 bg-accent/15" : "border-border bg-background/35")}>
                          {isComplete ? "✓" : isActive ? "●" : index + 1}
                        </span>
                        <div>
                          <p className="font-black">{stage.label}</p>
                          <p className="mt-1 text-[0.68rem] leading-4 text-muted-foreground">{stage.detail}</p>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            </div>
          )}

          <div className="flex flex-col-reverse gap-3 border-t border-border/70 pt-5 sm:flex-row sm:flex-wrap sm:justify-end">
            {status === "complete" && !analysisStage && (
              <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={clearSelection}>
                Upload another
              </Button>
            )}
            {status === "complete" && uploadId && (
              <Button type="button" className="w-full sm:w-auto" onClick={startAnalysis}>
                Analyze Video
              </Button>
            )}
            <Button type="button" className="w-full sm:w-auto" disabled={!file || !sport || status !== "ready"} onClick={startUpload}>
              Upload video
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
