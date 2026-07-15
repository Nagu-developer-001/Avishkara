import json
import uuid
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import COMPLETED_STATUS
from app.models.pose_processing import PoseProcessingResult
from app.models.video import VideoUpload
from app.schemas.benchmark import BenchmarkScores, PhaseBenchmarkScores
from app.schemas.biomechanics import (
    AnalysisConfidence,
    BilateralAngleMetric,
    BiomechanicalMetrics,
    CoachReplayFrame,
    CoachReplayTimeline,
    DistanceMetric,
    PhaseBiomechanicalMetrics,
    RunningBiomechanicsMetrics,
)
from app.schemas.pose import PoseFrame
from app.services.benchmark import BenchmarkEngine
from app.services.benchmark_loader import load_benchmark
from app.services.biomechanics import BiomechanicsService
from app.services.phase_detection import PhaseDetectionError, PhaseDetectionService
from app.services.running_gait_analysis import RunningGaitAnalysisService
from app.services.video_quality import FULL_BODY_LANDMARKS, MIN_LANDMARK_VISIBILITY


class AnalysisUploadNotFoundError(LookupError):
    pass


class PoseProcessingRequiredError(RuntimeError):
    pass


class NoPoseDetectedError(ValueError):
    pass


class StoredAnalysisService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_biomechanics(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> BiomechanicalMetrics:
        upload = await self._load_upload(upload_id, athlete_id)
        return await self._calculate_for_upload(upload)

    async def calculate_leaderboard_biomechanics(
        self, *, upload_id: uuid.UUID
    ) -> BiomechanicalMetrics:
        upload = await self._load_completed_upload(upload_id)
        return await self._calculate_for_upload(upload)

    async def coach_replay(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> CoachReplayTimeline:
        upload = await self._load_upload(upload_id, athlete_id)
        return await self._coach_replay_for_upload(upload)

    async def leaderboard_coach_replay(
        self, *, upload_id: uuid.UUID
    ) -> CoachReplayTimeline:
        upload = await self._load_completed_upload(upload_id)
        return await self._coach_replay_for_upload(upload)

    async def analysis_confidence(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> AnalysisConfidence:
        upload = await self._load_upload(upload_id, athlete_id)
        return await self._analysis_confidence_for_upload(upload)

    async def leaderboard_analysis_confidence(
        self, *, upload_id: uuid.UUID
    ) -> AnalysisConfidence:
        upload = await self._load_completed_upload(upload_id)
        return await self._analysis_confidence_for_upload(upload)

    async def _calculate_for_upload(self, upload: VideoUpload) -> BiomechanicalMetrics:
        upload_id = upload.id
        processing = await self._load_processing(upload_id)
        landmark_path = Path(processing.landmark_file)
        if not landmark_path.is_file():
            raise PoseProcessingRequiredError(upload_id)

        payload = await run_in_threadpool(self._read_json, landmark_path)
        frames = self._pose_frames(payload)
        if not frames:
            raise NoPoseDetectedError("No complete pose was detected in the video")

        metrics = [BiomechanicsService().calculate(frame) for frame in frames]
        metrics_by_frame = {metric.frame_index: metric for metric in metrics}
        detected_phases = PhaseDetectionService().detect(frames, upload.sport)
        phase_metrics = []
        for phase in detected_phases:
            selected = [
                metrics_by_frame[index]
                for index in phase.frame_indexes
                if index in metrics_by_frame
            ]
            if not selected:
                continue
            average = self._average_metrics(selected)
            phase_metrics.append(
                PhaseBiomechanicalMetrics(
                    movement_phase=phase.name,
                    start_frame=phase.start_frame,
                    end_frame=phase.end_frame,
                    frame_count=len(selected),
                    knee_angle=average.knee_angle,
                    elbow_angle=average.elbow_angle,
                    hip_angle=average.hip_angle,
                    stride_length=average.stride_length,
                )
            )
        running = (
            RunningGaitAnalysisService().analyze(frames)
            if upload.sport.casefold() == "running"
            else None
        )
        return self._average_metrics(metrics, phases=phase_metrics, running=running)

    async def _coach_replay_for_upload(self, upload: VideoUpload) -> CoachReplayTimeline:
        processing = await self._load_processing(upload.id)
        landmark_path = Path(processing.landmark_file)
        if not landmark_path.is_file():
            raise PoseProcessingRequiredError(upload.id)

        payload = await run_in_threadpool(self._read_json, landmark_path)
        frames = self._pose_frames(payload)
        if not frames:
            raise NoPoseDetectedError("No complete pose was detected in the video")

        phase_by_frame = self._phase_by_frame(frames, upload.sport)
        metrics = [BiomechanicsService().calculate(frame) for frame in frames]
        return CoachReplayTimeline(
            upload_id=str(upload.id),
            total_frames=processing.total_frames,
            processed_frames=processing.processed_frames,
            frames=[
                CoachReplayFrame(
                    frame_index=metric.frame_index,
                    timestamp_ms=metric.timestamp_ms,
                    movement_phase=phase_by_frame.get(metric.frame_index, "Movement"),
                    knee_angle=metric.knee_angle,
                    elbow_angle=metric.elbow_angle,
                    hip_angle=metric.hip_angle,
                    stride_length=metric.stride_length,
                )
                for metric in metrics
            ],
        )

    async def _analysis_confidence_for_upload(self, upload: VideoUpload) -> AnalysisConfidence:
        processing = await self._load_processing(upload.id)
        landmark_path = Path(processing.landmark_file)
        if not landmark_path.is_file():
            raise PoseProcessingRequiredError(upload.id)

        payload = await run_in_threadpool(self._read_json, landmark_path)
        raw_frames = payload.get("frames", [])
        detected_frames = [
            frame for frame in raw_frames if len(frame.get("landmarks", [])) == 33
        ]
        full_body_frames = [
            frame for frame in detected_frames if self._has_full_body(frame)
        ]
        processed_frames = max(
            int(payload.get("processedFrames", processing.processed_frames)), 1
        )
        pose_detection_ratio = min(1.0, len(detected_frames) / processed_frames)
        full_body_ratio = (
            len(full_body_frames) / len(detected_frames)
            if detected_frames
            else 0.0
        )
        visibility = self._average_visibility(full_body_frames or detected_frames)
        gait_score, gait_label = await self._gait_reliability(upload, detected_frames)

        score = round(
            40 * pose_detection_ratio
            + 35 * full_body_ratio
            + 15 * visibility
            + 10 * gait_score,
            1,
        )
        warnings = self._confidence_warnings(
            pose_detection_ratio=pose_detection_ratio,
            full_body_ratio=full_body_ratio,
            visibility=visibility,
            gait_label=gait_label,
        )
        return AnalysisConfidence(
            score=score,
            rating=self._confidence_rating(score),
            pose_detection_ratio=round(pose_detection_ratio, 3),
            full_body_visibility_ratio=round(full_body_ratio, 3),
            average_landmark_visibility=round(visibility, 3),
            gait_reliability=gait_label,
            warnings=warnings,
        )

    async def compare_benchmark(
        self,
        *,
        upload_id: uuid.UUID,
        athlete_id: uuid.UUID,
        metrics: BiomechanicalMetrics,
    ) -> BenchmarkScores:
        upload = await self._load_upload(upload_id, athlete_id)
        baseline = BenchmarkEngine(load_benchmark(upload.sport)).compare(metrics)
        if not metrics.phases:
            return baseline

        phase_scores = []
        for phase in metrics.phases:
            phase_input = BiomechanicalMetrics(
                frame_index=phase.start_frame,
                timestamp_ms=0,
                knee_angle=phase.knee_angle,
                elbow_angle=phase.elbow_angle,
                hip_angle=phase.hip_angle,
                stride_length=phase.stride_length,
            )
            scores = BenchmarkEngine(
                load_benchmark(upload.sport, phase.movement_phase)
            ).compare(phase_input)
            phase_scores.append(
                PhaseBenchmarkScores(
                    movement_phase=phase.movement_phase,
                    start_frame=phase.start_frame,
                    end_frame=phase.end_frame,
                    frame_count=phase.frame_count,
                    technique_score=scores.technique_score,
                    efficiency_score=scores.efficiency_score,
                    balance_score=scores.balance_score,
                    overall_score=scores.overall_score or 0,
                    metric_deviations=scores.metric_deviations,
                )
            )
        total_frames = sum(score.frame_count for score in phase_scores)

        def weighted(field: str) -> float:
            return round(
                sum(
                    getattr(score, field) * score.frame_count
                    for score in phase_scores
                )
                / total_frames,
                2,
            )

        return BenchmarkScores(
            technique_score=weighted("technique_score"),
            efficiency_score=weighted("efficiency_score"),
            balance_score=weighted("balance_score"),
            overall_score=weighted("overall_score"),
            metric_deviations=baseline.metric_deviations,
            phase_scores=phase_scores,
        )

    @staticmethod
    def _phase_by_frame(frames: list[PoseFrame], sport: str) -> dict[int, str]:
        try:
            phases = PhaseDetectionService().detect(frames, sport)
        except PhaseDetectionError:
            return {}
        return {
            frame_index: phase.name
            for phase in phases
            for frame_index in phase.frame_indexes
        }

    async def _gait_reliability(
        self, upload: VideoUpload, detected_frames: list[dict]
    ) -> tuple[float, str | None]:
        if upload.sport.casefold() != "running":
            return 1.0, None
        try:
            frames = self._pose_frames({"frames": detected_frames})
            running = RunningGaitAnalysisService().analyze(frames)
        except (NoPoseDetectedError, PoseProcessingRequiredError, ValidationError):
            return 0.0, "Low"
        reliable = (
            running.step_count >= 6
            and len(running.stride_analysis.foot_strikes) >= 6
            and len(running.stride_analysis.step_intervals) >= 5
        )
        return (1.0, "Reliable") if reliable else (0.35, "Low")

    @staticmethod
    def _has_full_body(frame: dict) -> bool:
        landmarks = {
            landmark.get("name"): landmark
            for landmark in frame.get("landmarks", [])
        }
        return all(
            name in landmarks
            and (landmarks[name].get("visibility") or 0) >= MIN_LANDMARK_VISIBILITY
            and 0 <= landmarks[name].get("x", -1) <= 1
            and 0 <= landmarks[name].get("y", -1) <= 1
            for name in FULL_BODY_LANDMARKS
        )

    @staticmethod
    def _average_visibility(frames: list[dict]) -> float:
        values = [
            landmark.get("visibility") or 0
            for frame in frames
            for landmark in frame.get("landmarks", [])
            if landmark.get("name") in FULL_BODY_LANDMARKS
        ]
        if not values:
            return 0.0
        return min(1.0, max(0.0, sum(values) / len(values)))

    @staticmethod
    def _confidence_rating(score: float) -> str:
        if score >= 85:
            return "High"
        if score >= 70:
            return "Good"
        if score >= 50:
            return "Moderate"
        return "Low"

    @staticmethod
    def _confidence_warnings(
        *,
        pose_detection_ratio: float,
        full_body_ratio: float,
        visibility: float,
        gait_label: str | None,
    ) -> list[str]:
        warnings: list[str] = []
        if pose_detection_ratio < 0.65:
            warnings.append("Pose was not detected consistently across the video.")
        if full_body_ratio < 0.7:
            warnings.append("Full body was not visible in enough frames.")
        if visibility < 0.65:
            warnings.append("Important body landmarks had low visibility.")
        if gait_label == "Low":
            warnings.append("Running gait events were not reliable enough for stride timing.")
        return warnings

    async def _load_upload(
        self, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> VideoUpload:
        result = await self.session.execute(
            select(VideoUpload).where(
                VideoUpload.id == upload_id,
                VideoUpload.athlete_id == athlete_id,
            )
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise AnalysisUploadNotFoundError(upload_id)
        return upload

    async def _load_completed_upload(self, upload_id: uuid.UUID) -> VideoUpload:
        result = await self.session.execute(
            select(VideoUpload).where(
                VideoUpload.id == upload_id,
                VideoUpload.status == COMPLETED_STATUS,
            )
        )
        upload = result.scalar_one_or_none()
        if upload is None:
            raise AnalysisUploadNotFoundError(upload_id)
        return upload

    async def _load_processing(
        self, upload_id: uuid.UUID
    ) -> PoseProcessingResult:
        result = await self.session.execute(
            select(PoseProcessingResult).where(
                PoseProcessingResult.upload_id == upload_id
            )
        )
        processing = result.scalar_one_or_none()
        if processing is None:
            raise PoseProcessingRequiredError(upload_id)
        return processing

    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _pose_frames(payload: dict) -> list[PoseFrame]:
        frames: list[PoseFrame] = []
        try:
            for frame in payload.get("frames", []):
                if len(frame.get("landmarks", [])) != 33:
                    continue
                frames.append(
                    PoseFrame(
                        frame_index=frame["frameIndex"],
                        timestamp_ms=frame["timestampMs"],
                        landmarks=frame["landmarks"],
                    )
                )
        except (KeyError, TypeError, ValidationError) as exc:
            raise PoseProcessingRequiredError("Invalid landmark data") from exc
        return frames

    @staticmethod
    def _average_metrics(
        metrics: list[BiomechanicalMetrics],
        *,
        phases: list[PhaseBiomechanicalMetrics] | None = None,
        running: RunningBiomechanicsMetrics | None = None,
    ) -> BiomechanicalMetrics:
        count = len(metrics)

        def mean(values: list[float]) -> float:
            return round(sum(values) / count, 2)

        def bilateral(name: str) -> BilateralAngleMetric:
            values = [getattr(metric, name) for metric in metrics]
            return BilateralAngleMetric(
                left=mean([value.left for value in values]),
                right=mean([value.right for value in values]),
            )

        return BiomechanicalMetrics(
            frame_index=metrics[0].frame_index,
            timestamp_ms=metrics[0].timestamp_ms,
            knee_angle=bilateral("knee_angle"),
            elbow_angle=bilateral("elbow_angle"),
            hip_angle=bilateral("hip_angle"),
            stride_length=DistanceMetric(
                value=round(
                    sum(metric.stride_length.value for metric in metrics) / count,
                    4,
                ),
                unit=metrics[0].stride_length.unit,
            ),
            phases=phases or [],
            running=running,
        )
