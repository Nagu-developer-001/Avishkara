from pathlib import Path

import cv2

from app.schemas.pose import (
    FullVideoPoseResult,
    PoseFrame,
    PoseLandmark,
    ProcessedPoseFrame,
)
from app.services.biomechanics import BiomechanicsService


POSE_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20),
    (16, 22), (18, 20), (11, 23), (12, 24),
    (23, 24), (23, 25), (25, 27), (27, 29),
    (29, 31), (27, 31), (24, 26), (26, 28),
    (28, 30), (30, 32), (28, 32),
)

MEASURED_JOINTS = {
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
}

MAX_PREVIEW_DIMENSION = 1280


class VisualizationError(ValueError):
    pass


class BiomechanicalVisualizationService:
    def generate(
        self,
        *,
        video_path: Path,
        pose_result: FullVideoPoseResult,
        output_path: Path,
    ) -> Path:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            raise VisualizationError(f"Unable to open video: {video_path}")

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            capture.release()
            raise VisualizationError("Video does not contain valid dimensions")
        output_width, output_height = self._preview_size(width, height)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(f"{output_path.stem}.tmp.mp4")
        writer = self._create_writer(
            temporary_path=temporary_path,
            fps=pose_result.fps,
            size=(output_width, output_height),
        )
        if not writer.isOpened():
            capture.release()
            raise VisualizationError("Unable to create annotated preview video")

        frames = {frame.frame_index: frame for frame in pose_result.frames}
        frame_index = 0
        try:
            while True:
                success, image = capture.read()
                if not success:
                    break
                if (output_width, output_height) != (width, height):
                    image = cv2.resize(
                        image,
                        (output_width, output_height),
                        interpolation=cv2.INTER_AREA,
                    )
                pose_frame = frames.get(frame_index)
                if pose_frame and pose_frame.landmarks:
                    self._annotate(image, pose_frame.landmarks, pose_frame)
                writer.write(image)
                frame_index += 1
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        finally:
            capture.release()
            writer.release()

        if (
            frame_index == 0
            or not temporary_path.is_file()
            or temporary_path.stat().st_size == 0
            or not self._is_readable_video(temporary_path)
        ):
            temporary_path.unlink(missing_ok=True)
            raise VisualizationError("No frames were written to the annotated preview")
        temporary_path.replace(output_path)
        return output_path

    @staticmethod
    def _create_writer(
        *, temporary_path: Path, fps: float, size: tuple[int, int]
    ) -> cv2.VideoWriter:
        for codec in ("avc1", "H264", "X264", "mp4v"):
            writer = cv2.VideoWriter(
                str(temporary_path),
                cv2.VideoWriter_fourcc(*codec),
                fps,
                size,
            )
            if writer.isOpened():
                return writer
            writer.release()
        return cv2.VideoWriter()

    @staticmethod
    def _preview_size(width: int, height: int) -> tuple[int, int]:
        longest_side = max(width, height)
        if longest_side <= MAX_PREVIEW_DIMENSION:
            return width, height
        scale = MAX_PREVIEW_DIMENSION / longest_side
        output_width = max(2, int(round(width * scale)))
        output_height = max(2, int(round(height * scale)))
        if output_width % 2:
            output_width -= 1
        if output_height % 2:
            output_height -= 1
        return output_width, output_height

    @staticmethod
    def _is_readable_video(path: Path) -> bool:
        capture = cv2.VideoCapture(str(path))
        try:
            success, _ = capture.read()
            return bool(success)
        finally:
            capture.release()

    @staticmethod
    def _annotate(
        image, landmarks: list[PoseLandmark], pose_frame: ProcessedPoseFrame
    ) -> None:
        height, width = image.shape[:2]
        points = {
            landmark.index: (
                int(min(max(landmark.x, 0), 1) * (width - 1)),
                int(min(max(landmark.y, 0), 1) * (height - 1)),
            )
            for landmark in landmarks
        }
        by_name = {landmark.name: landmark for landmark in landmarks}

        for start, end in POSE_CONNECTIONS:
            if start in points and end in points:
                cv2.line(image, points[start], points[end], (0, 220, 255), 3, cv2.LINE_AA)

        for landmark in landmarks:
            point = points[landmark.index]
            measured = landmark.name in MEASURED_JOINTS
            color = (40, 80, 255) if measured else (255, 255, 255)
            radius = 7 if measured else 4
            cv2.circle(image, point, radius, color, -1, cv2.LINE_AA)

        try:
            metrics = BiomechanicsService().calculate(
                PoseFrame(
                    frame_index=pose_frame.frame_index,
                    timestamp_ms=pose_frame.timestamp_ms,
                    landmarks=landmarks,
                )
            )
        except ValueError:
            return
        labels = (
            ("left_knee", f"K {metrics.knee_angle.left:.1f} deg"),
            ("right_knee", f"K {metrics.knee_angle.right:.1f} deg"),
            ("left_elbow", f"E {metrics.elbow_angle.left:.1f} deg"),
            ("right_elbow", f"E {metrics.elbow_angle.right:.1f} deg"),
            ("left_hip", f"H {metrics.hip_angle.left:.1f} deg"),
            ("right_hip", f"H {metrics.hip_angle.right:.1f} deg"),
        )
        for name, text in labels:
            landmark = by_name[name]
            x, y = points[landmark.index]
            BiomechanicalVisualizationService._draw_label(image, text, x + 8, y - 8)

    @staticmethod
    def _draw_label(image, text: str, x: int, y: int) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.48
        thickness = 1
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, scale, thickness
        )
        x = max(0, min(x, image.shape[1] - text_width - 8))
        y = max(text_height + 8, min(y, image.shape[0] - baseline - 4))
        cv2.rectangle(
            image,
            (x - 4, y - text_height - 5),
            (x + text_width + 4, y + baseline + 3),
            (8, 15, 28),
            -1,
        )
        cv2.putText(
            image, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA
        )
