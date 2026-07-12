import uuid
from dataclasses import dataclass
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path

import cv2
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.upload import COMPLETED_STATUS
from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.athlete_profile import AthleteProfile
from app.models.user import User
from app.models.video import VideoUpload
from app.schemas.benchmark import BenchmarkScores, MetricDeviation
from app.schemas.biomechanics import BiomechanicalMetrics, RunningBiomechanicsMetrics
from app.schemas.recommendation import RecommendationResult
from app.services.stored_analysis import (
    AnalysisUploadNotFoundError,
    NoPoseDetectedError,
    PoseProcessingRequiredError,
    StoredAnalysisService,
)
from app.services.video_processing import VideoProcessingService


class ReportNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class ReportPayload:
    upload_id: uuid.UUID
    athlete_id: uuid.UUID
    assessment_id: uuid.UUID
    athlete_name: str
    age: int
    gender: str
    state: str
    profile_sport: str
    experience: int
    assessment_sport: str
    assessment_date: datetime
    video_path: Path
    annotated_video_path: Path | None
    scores: BenchmarkScores
    biomechanics: BiomechanicalMetrics | None
    recommendations: RecommendationResult


class AssessmentReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_athlete(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> tuple[bytes, str]:
        payload = await self._payload(
            VideoUpload.id == upload_id,
            VideoUpload.athlete_id == athlete_id,
        )
        return AssessmentPdfRenderer().render(payload), self._filename(payload)

    async def for_authority(
        self, *, assessment_id: uuid.UUID
    ) -> tuple[bytes, str]:
        payload = await self._payload(Assessment.id == assessment_id)
        return AssessmentPdfRenderer().render(payload), self._filename(payload)

    async def for_leaderboard(
        self, *, upload_id: uuid.UUID
    ) -> tuple[bytes, str]:
        payload = await self._payload(
            VideoUpload.id == upload_id,
            VideoUpload.status == COMPLETED_STATUS,
        )
        return AssessmentPdfRenderer().render(payload), self._filename(payload)

    async def _payload(self, *conditions) -> ReportPayload:
        result = await self.session.execute(
            select(
                User,
                AthleteProfile,
                VideoUpload,
                Assessment,
                AssessmentSnapshot,
            )
            .join(AthleteProfile, AthleteProfile.user_id == User.id)
            .join(VideoUpload, VideoUpload.athlete_id == User.id)
            .join(Assessment, Assessment.upload_id == VideoUpload.id)
            .join(AssessmentSnapshot, AssessmentSnapshot.upload_id == VideoUpload.id)
            .where(*conditions)
        )
        row = result.one_or_none()
        if row is None:
            raise ReportNotFoundError
        user, profile, upload, assessment, snapshot = row
        biomechanics = await self._safe_biomechanics(
            upload_id=upload.id,
            athlete_id=user.id,
        )
        annotated_video_path = VideoProcessingService.annotated_path(user.id, upload.id)
        return ReportPayload(
            upload_id=upload.id,
            athlete_id=user.id,
            assessment_id=assessment.id,
            athlete_name=user.name,
            age=profile.age,
            gender=profile.gender,
            state=profile.state,
            profile_sport=profile.sport,
            experience=profile.experience,
            assessment_sport=upload.sport,
            assessment_date=upload.upload_time,
            video_path=Path(upload.temporary_path),
            annotated_video_path=(
                annotated_video_path if annotated_video_path.is_file() else None
            ),
            scores=BenchmarkScores.model_validate(snapshot.benchmark_result),
            biomechanics=biomechanics,
            recommendations=RecommendationResult(
                strengths=assessment.strengths,
                weaknesses=assessment.weaknesses,
                improvement_suggestions=assessment.improvement_suggestions,
            ),
        )

    async def _safe_biomechanics(
        self, *, upload_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> BiomechanicalMetrics | None:
        try:
            return await StoredAnalysisService(self.session).calculate_biomechanics(
                upload_id=upload_id,
                athlete_id=athlete_id,
            )
        except (
            AnalysisUploadNotFoundError,
            PoseProcessingRequiredError,
            NoPoseDetectedError,
        ):
            return None

    @staticmethod
    def _filename(payload: ReportPayload) -> str:
        safe_name = "-".join(payload.athlete_name.lower().split())
        return f"avishkara-{safe_name}-{payload.assessment_id}.pdf"


class AssessmentPdfRenderer:
    navy = colors.HexColor("#071019")
    panel = colors.HexColor("#101C29")
    lime = colors.HexColor("#A3E635")
    cyan = colors.HexColor("#22D3EE")
    pale = colors.HexColor("#E8EEF4")
    muted = colors.HexColor("#91A0AE")
    line = colors.HexColor("#263746")

    def __init__(self):
        styles = getSampleStyleSheet()
        self.title = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=29,
            textColor=self.navy,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        )
        self.subtitle = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#526170"),
            alignment=TA_CENTER,
        )
        self.heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=self.navy,
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
        )
        self.body = ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontSize=9.2,
            leading=13,
            textColor=colors.HexColor("#253442"),
        )
        self.small = ParagraphStyle(
            "ReportSmall",
            parent=styles["BodyText"],
            fontSize=7.8,
            leading=10.5,
            textColor=colors.HexColor("#526170"),
        )

    def render(self, payload: ReportPayload) -> bytes:
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=17 * mm,
            bottomMargin=18 * mm,
            title=f"Avishkara Assessment - {payload.athlete_name}",
            author="Avishkara Sports Intelligence",
        )
        story = [
            Paragraph("AVISHKARA", self.title),
            Paragraph(
                "BIOMECHANICAL PERFORMANCE ASSESSMENT REPORT",
                self.subtitle,
            ),
            Spacer(1, 6 * mm),
            self._identity_table(payload),
            Spacer(1, 5 * mm),
        ]
        story.extend(self._video_evidence(payload))
        story.extend(
            [
                Paragraph("Performance Scores", self.heading),
                self._score_table(payload.scores),
                Spacer(1, 4 * mm),
            ]
        )
        if payload.scores.phase_scores:
            story.extend(
                [
                    Paragraph("Movement Phase Scores", self.heading),
                    self._phase_table(payload.scores),
                    Spacer(1, 4 * mm),
                ]
            )
        if payload.biomechanics is not None:
            story.extend(
                [
                    Paragraph("Pose-Derived Biomechanics", self.heading),
                    self._biomechanics_table(payload.biomechanics),
                    Spacer(1, 4 * mm),
                ]
            )
            if payload.biomechanics.running is not None:
                story.append(PageBreak())
                story.append(Paragraph("Running Gait Intelligence", self.heading))
                if self._has_reliable_running_gait(payload.biomechanics.running):
                    story.extend(
                        [
                            self._running_summary(payload.biomechanics.running),
                            Spacer(1, 4 * mm),
                            self._running_events_table(payload.biomechanics.running),
                            Spacer(1, 4 * mm),
                            self._running_stride_table(payload.biomechanics.running),
                            Spacer(1, 4 * mm),
                        ]
                    )
                else:
                    story.extend(
                        [
                            self._empty_table(
                                "Running gait timeline and foot landings were not included because the system could not detect enough reliable alternating foot strikes for this clip."
                            ),
                            Spacer(1, 4 * mm),
                        ]
                    )
        story.extend(
            [
                PageBreak(),
                Paragraph("Biomechanical Metrics and Benchmark Comparison", self.heading),
                self._metrics_table(payload.scores),
                Spacer(1, 4 * mm),
                Paragraph("Assessment Recommendations", self.heading),
                *self._recommendations(payload.recommendations),
                Spacer(1, 6 * mm),
                self._method_note(),
            ]
        )
        document.build(
            story,
            onFirstPage=self._page_decoration,
            onLaterPages=self._page_decoration,
        )
        return output.getvalue()

    def _identity_table(self, payload: ReportPayload) -> Table:
        data = [
            ["ATHLETE", payload.athlete_name, "SPORT", payload.assessment_sport],
            ["AGE", str(payload.age), "GENDER", payload.gender],
            ["STATE", payload.state, "EXPERIENCE", f"{payload.experience} years"],
            ["DATE", payload.assessment_date.strftime("%d %b %Y"), "ASSESSMENT ID", str(payload.assessment_id)],
        ]
        table = Table(data, colWidths=[26 * mm, 55 * mm, 29 * mm, 68 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F8")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), self.navy),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#647483")),
                    ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#647483")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E0E6")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _video_evidence(self, payload: ReportPayload) -> list:
        original = self._thumbnail(
            payload.video_path,
            "SOURCE FOOTAGE",
            colors.HexColor("#22D3EE"),
            width=86 * mm,
            height=48 * mm,
        )
        annotated = (
            self._thumbnail(
                payload.annotated_video_path,
                "ANNOTATED ANALYSIS",
                colors.HexColor("#A3E635"),
                width=86 * mm,
                height=48 * mm,
            )
            if payload.annotated_video_path is not None
            else None
        )
        if original is None and annotated is None:
            return []

        cells = []
        for title, subtitle, image in [
            ("Original Movement", "Uploaded source footage", original),
            ("Biomechanical Overlay", "Annotated skeleton preview", annotated),
        ]:
            if image is None:
                body = self._empty_table("Preview not available", width=86 * mm)
            else:
                body = image
            cells.append(
                [
                    Paragraph(f"<b>{self._clean(title)}</b>", self.body),
                    Paragraph(self._clean(subtitle), self.small),
                    Spacer(1, 1.5 * mm),
                    body,
                ]
            )

        table = Table([cells], colWidths=[88 * mm, 88 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return [
            Paragraph("Video Evidence", self.heading),
            table,
            Spacer(1, 4 * mm),
        ]

    def _thumbnail(
        self,
        video_path: Path | None,
        label: str,
        accent: colors.Color,
        *,
        width: float,
        height: float,
    ) -> Image | None:
        if video_path is None:
            return None
        if not video_path.is_file():
            return None
        capture = cv2.VideoCapture(str(video_path))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 1:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 3)
        success, frame = capture.read()
        capture.release()
        if not success:
            return None
        frame = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
        cv2.rectangle(frame, (0, 0), (960, 58), (7, 16, 25), -1)
        cv2.putText(
            frame,
            f"AVISHKARA - {label}",
            (24, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (
                int(accent.blue * 255),
                int(accent.green * 255),
                int(accent.red * 255),
            ),
            2,
            cv2.LINE_AA,
        )
        encoded, image_data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if not encoded:
            return None
        return Image(BytesIO(image_data.tobytes()), width=width, height=height)

    def _score_table(self, scores: BenchmarkScores) -> Table:
        values = [
            ("TECHNIQUE", scores.technique_score),
            ("EFFICIENCY", scores.efficiency_score),
            ("BALANCE", scores.balance_score),
            ("OVERALL", scores.overall_score),
        ]
        data = [[label for label, _ in values], [self._score(value) for _, value in values]]
        table = Table(data, colWidths=[44.5 * mm] * 4, rowHeights=[10 * mm, 16 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.navy),
                    ("TEXTCOLOR", (0, 0), (-1, 0), self.muted),
                    ("TEXTCOLOR", (0, 1), (-1, 1), self.lime),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTSIZE", (0, 1), (-1, 1), 22),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.6, self.line),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, self.line),
                ]
            )
        )
        return table

    def _metrics_table(self, scores: BenchmarkScores) -> Table:
        deviations = scores.metric_deviations
        if deviations is None:
            return self._empty_table(
                "Detailed biomechanical metrics were not stored for this assessment."
            )
        rows = [
            ("Left knee angle", deviations.knee_angle.left),
            ("Right knee angle", deviations.knee_angle.right),
            ("Left elbow angle", deviations.elbow_angle.left),
            ("Right elbow angle", deviations.elbow_angle.right),
            ("Left hip angle", deviations.hip_angle.left),
            ("Right hip angle", deviations.hip_angle.right),
            ("Stride length", deviations.stride_length),
        ]
        data = [["METRIC", "MEASURED", "BENCHMARK", "DEVIATION"]]
        data.extend(
            [label, self._metric(metric.actual, metric), self._metric(metric.target, metric), self._signed(metric.signed_deviation, metric)]
            for label, metric in rows
        )
        table = Table(data, colWidths=[57 * mm, 40 * mm, 40 * mm, 41 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.panel),
                    ("TEXTCOLOR", (0, 0), (-1, 0), self.pale),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F9")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DFE5")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _phase_table(self, scores: BenchmarkScores) -> Table:
        data = [
            [
                "PHASE",
                "FRAMES",
                "TECHNIQUE",
                "EFFICIENCY",
                "BALANCE",
                "OVERALL",
            ]
        ]
        data.extend(
            [
                self._clean(phase.movement_phase),
                f"{phase.start_frame}-{phase.end_frame}",
                self._score(phase.technique_score),
                self._score(phase.efficiency_score),
                self._score(phase.balance_score),
                self._score(phase.overall_score),
            ]
            for phase in scores.phase_scores
        )
        table = Table(
            data,
            colWidths=[43 * mm, 28 * mm, 27 * mm, 27 * mm, 25 * mm, 28 * mm],
            repeatRows=1,
        )
        table.setStyle(self._standard_table_style())
        return table

    def _biomechanics_table(self, metrics: BiomechanicalMetrics) -> Table:
        data = [["METRIC", "LEFT", "RIGHT", "UNIT"]]
        data.extend(
            [
                [
                    "Knee angle",
                    f"{metrics.knee_angle.left:.2f}",
                    f"{metrics.knee_angle.right:.2f}",
                    "degrees",
                ],
                [
                    "Elbow angle",
                    f"{metrics.elbow_angle.left:.2f}",
                    f"{metrics.elbow_angle.right:.2f}",
                    "degrees",
                ],
                [
                    "Hip angle",
                    f"{metrics.hip_angle.left:.2f}",
                    f"{metrics.hip_angle.right:.2f}",
                    "degrees",
                ],
                [
                    "Stride length",
                    f"{metrics.stride_length.value:.4f}",
                    "-",
                    metrics.stride_length.unit.replace("_", " "),
                ],
            ]
        )
        table = Table(data, colWidths=[58 * mm, 38 * mm, 38 * mm, 44 * mm])
        table.setStyle(self._standard_table_style())
        return table

    def _running_summary(self, running: RunningBiomechanicsMetrics) -> Table:
        cards = [
            ("Cadence", self._optional(running.cadence_spm, " spm")),
            ("Contact Time", self._optional(running.contact_time_ms, " ms")),
            ("Flight Time", self._optional(running.flight_time_ms, " ms")),
            ("Duty Factor", self._optional(running.duty_factor_pct, "%")),
            (
                "Stride Symmetry",
                self._optional(running.stride_time_symmetry_pct, "%"),
            ),
            (
                "Vertical Oscillation",
                self._optional(running.vertical_oscillation_ratio_pct, "%"),
            ),
        ]
        data = [
            [Paragraph(f"<b>{label}</b><br/>{value}", self.body) for label, value in cards[:3]],
            [Paragraph(f"<b>{label}</b><br/>{value}", self.body) for label, value in cards[3:]],
        ]
        table = Table(data, colWidths=[59.3 * mm] * 3)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F8FA")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), self.navy),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E5EA")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6E5EA")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def _running_events_table(self, running: RunningBiomechanicsMetrics) -> Table:
        data = [
            ["EVENT / MEASURE", "VALUE"],
            ["Detected steps", str(running.step_count)],
            ["Left steps", str(running.left_step_count)],
            ["Right steps", str(running.right_step_count)],
            [
                "Left foot strikes",
                str(len(running.gait_events.left_foot_strikes)),
            ],
            [
                "Right foot strikes",
                str(len(running.gait_events.right_foot_strikes)),
            ],
            ["Left toe-offs", str(len(running.gait_events.left_toe_offs))],
            ["Right toe-offs", str(len(running.gait_events.right_toe_offs))],
            ["Duration", self._optional(running.duration_seconds, " sec")],
            ["Mean stride time", self._optional(running.mean_stride_time_ms, " ms")],
            ["Stride length", self._optional(running.stride_length_norm, " leg lengths")],
            ["Overstriding index", self._optional(running.overstriding_index_pct, "%")],
            ["Trunk lean", self._optional(running.trunk_lean_deg, " deg")],
            [
                "Knee flexion at contact",
                self._optional(running.knee_flex_at_contact_deg, " deg"),
            ],
            [
                "Hip extension max",
                self._optional(running.hip_extension_max_deg, " deg"),
            ],
            [
                "Arm swing amplitude",
                self._optional(running.arm_swing_amplitude_deg, " deg"),
            ],
            [
                "Contact time symmetry",
                self._optional(running.contact_time_symmetry_pct, "%"),
            ],
            [
                "Knee angle symmetry",
                self._optional(running.knee_angle_symmetry_pct, "%"),
            ],
        ]
        table = Table(data, colWidths=[98 * mm, 80 * mm], repeatRows=1)
        table.setStyle(self._standard_table_style())
        return table

    def _running_stride_table(self, running: RunningBiomechanicsMetrics) -> Table:
        intervals = running.stride_analysis.stride_intervals[:10]
        if not intervals:
            return self._empty_table("Stride intervals were not detected for this clip.")
        data = [["SIDE", "START FRAME", "END FRAME", "DURATION", "LENGTH"]]
        data.extend(
            [
                self._clean(interval.side.title()),
                str(interval.start_frame),
                str(interval.end_frame),
                self._optional(interval.duration_ms, " ms"),
                self._optional(interval.stride_length_norm, " leg lengths"),
            ]
            for interval in intervals
        )
        table = Table(
            data,
            colWidths=[32 * mm, 35 * mm, 35 * mm, 38 * mm, 38 * mm],
            repeatRows=1,
        )
        table.setStyle(self._standard_table_style())
        return table

    @staticmethod
    def _has_reliable_running_gait(running: RunningBiomechanicsMetrics) -> bool:
        return (
            running.step_count >= 6
            and len(running.stride_analysis.foot_strikes) >= 6
            and len(running.stride_analysis.step_intervals) >= 5
        )

    def _recommendations(self, recommendations: RecommendationResult) -> list:
        sections = [
            ("Strengths", recommendations.strengths, colors.HexColor("#E9F8D7")),
            ("Weaknesses", recommendations.weaknesses, colors.HexColor("#FFF1DC")),
            ("Improvement Suggestions", recommendations.improvement_suggestions, colors.HexColor("#DFF5FA")),
        ]
        content = []
        for title, items, background in sections:
            paragraphs = [Paragraph(f"<b>{title}</b>", self.body)]
            paragraphs.extend(
                Paragraph(f"- {self._clean(item)}", self.body)
                for item in (items or ["None recorded."])
            )
            table = Table([[paragraphs]], colWidths=[178 * mm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), background),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD8DF")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )
            content.extend([KeepTogether(table), Spacer(1, 4 * mm)])
        return content

    def _method_note(self) -> Table:
        paragraph = Paragraph(
            "<b>Method note:</b> This report summarizes deterministic pose-derived biomechanics, sport-specific benchmark comparison, and rule-based recommendations. It does not replace professional coaching or medical assessment.",
            self.body,
        )
        table = Table([[paragraph]], colWidths=[178 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F5F7")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D9DF")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            )
        )
        return table

    def _empty_table(self, message: str, width: float = 178 * mm) -> Table:
        table = Table(
            [[Paragraph(self._clean(message), self.body)]],
            colWidths=[width],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F8")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E0E6")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return table

    def _standard_table_style(self) -> TableStyle:
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), self.panel),
                ("TEXTCOLOR", (0, 0), (-1, 0), self.pale),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F9")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DFE5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )

    def _page_decoration(self, canvas, document) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(self.navy)
        canvas.rect(0, height - 8 * mm, width, 8 * mm, fill=1, stroke=0)
        canvas.setFillColor(self.lime)
        canvas.rect(0, height - 8 * mm, 45 * mm, 8 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#D8E0E6"))
        canvas.line(16 * mm, 13 * mm, width - 16 * mm, 13 * mm)
        canvas.setFillColor(colors.HexColor("#71808C"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(16 * mm, 8 * mm, "Avishkara Sports Intelligence")
        canvas.drawRightString(width - 16 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    @staticmethod
    def _score(value: float | None) -> str:
        return "-" if value is None else f"{value:.1f}"

    @staticmethod
    def _metric(value: float, metric: MetricDeviation) -> str:
        unit = "deg" if metric.unit == "degrees" else metric.unit.replace("_", " ")
        return f"{value:.2f} {unit}"

    @staticmethod
    def _signed(value: float, metric: MetricDeviation) -> str:
        prefix = "+" if value > 0 else ""
        return f"{prefix}{AssessmentPdfRenderer._metric(value, metric)}"

    @staticmethod
    def _optional(value: float | None, suffix: str = "") -> str:
        if value is None:
            return "-"
        decimals = 0 if abs(value) >= 100 else 2
        return f"{value:.{decimals}f}{suffix}"

    @staticmethod
    def _clean(value: str) -> str:
        normalized = (
            value.replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2011", "-")
        )
        return escape(normalized)
