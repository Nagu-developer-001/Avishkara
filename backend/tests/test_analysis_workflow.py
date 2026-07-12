from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.constants.pose import POSE_LANDMARK_NAMES
from app.schemas.pose import (
    FullVideoPoseResult,
    PoseLandmark,
    ProcessedPoseFrame,
)
from app.utils.config import settings
from app.schemas.video_quality import VideoQualityResult


def register(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Workflow Athlete",
            "email": "workflow@example.com",
            "password": "secure-password-123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def extracted_pose() -> FullVideoPoseResult:
    coordinates = {
        "left_shoulder": (0.20, 0.20),
        "left_elbow": (0.20, 0.30),
        "left_wrist": (0.30, 0.30),
        "left_hip": (0.20, 0.50),
        "left_knee": (0.20, 0.70),
        "left_ankle": (0.40, 0.70),
        "right_shoulder": (0.70, 0.20),
        "right_elbow": (0.70, 0.30),
        "right_wrist": (0.60, 0.30),
        "right_hip": (0.70, 0.50),
        "right_knee": (0.70, 0.70),
        "right_ankle": (0.80, 0.70),
    }
    landmarks = []
    for index, name in enumerate(POSE_LANDMARK_NAMES):
        x, y = coordinates.get(name, (0.50, 0.50))
        landmarks.append(
            PoseLandmark(
                index=index,
                name=name,
                x=x,
                y=y,
                z=0,
                visibility=0.99,
                presence=0.99,
            )
        )
    frames = [
        ProcessedPoseFrame(
            frame_index=frame_index,
            timestamp_ms=frame_index * 33,
            landmarks=landmarks,
        )
        for frame_index in range(6)
    ]
    return FullVideoPoseResult(
        fps=30,
        total_frames=len(frames),
        processed_frames=len(frames),
        frames=frames,
    )


@pytest.fixture
def workflow_storage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "upload_directory", tmp_path / "uploads")
    monkeypatch.setattr(settings, "landmark_directory", tmp_path / "landmarks")
    monkeypatch.setattr(
        settings, "annotated_video_directory", tmp_path / "annotated_videos"
    )

    def fake_generate(self, video_path, pose_result, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"annotated-video")
        return output_path

    monkeypatch.setattr(
        "app.services.biomechanical_visualization.BiomechanicalVisualizationService.generate",
        fake_generate,
    )
    monkeypatch.setattr(
        "app.services.video_processing.VideoProcessingService._is_readable_video",
        staticmethod(lambda path: Path(path).is_file() and Path(path).stat().st_size > 0),
    )


def test_complete_analysis_workflow(
    client: TestClient,
    workflow_storage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = register(client)
    upload_response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Running"},
        files={"file": ("run.mp4", b"video-content", "video/mp4")},
    )
    upload_id = upload_response.json()["upload_id"]
    monkeypatch.setattr(
        "app.services.mediapipe_pose.MediaPipePoseService.extract_all",
        lambda self, video_path: extracted_pose(),
    )
    monkeypatch.setattr(
        "app.services.video_quality.VideoQualityService.validate",
        lambda self, pose, sport: VideoQualityResult(
            valid=True,
            reasons=[],
            detected_frames=1,
            full_body_frames=1,
        ),
    )

    processing = client.post(
        f"/api/v1/videos/{upload_id}/process", headers=headers
    )
    assert processing.status_code == 200, processing.text

    biomechanics = client.post(
        f"/api/v1/videos/{upload_id}/biomechanics", headers=headers
    )
    assert biomechanics.status_code == 200, biomechanics.text
    assert biomechanics.json()["knee_angle"] == {
        "left": 90.0,
        "right": 90.0,
        "unit": "degrees",
    }
    assert biomechanics.json()["running"] is not None
    assert biomechanics.json()["running"]["step_count"] >= 0

    benchmark = client.post(
        f"/api/v1/videos/{upload_id}/benchmark",
        headers=headers,
        json=biomechanics.json(),
    )
    assert benchmark.status_code == 200, benchmark.text
    assert benchmark.json()["overall_score"] == 100

    assessment = client.post(
        f"/api/v1/videos/{upload_id}/assessment",
        headers=headers,
        json=benchmark.json(),
    )
    assert assessment.status_code == 200, assessment.text

    results = client.get(
        f"/api/v1/videos/{upload_id}/results", headers=headers
    )
    history = client.get("/api/v1/videos/history", headers=headers)
    assert results.status_code == 200
    assert results.json()["video"]["status"] == "Completed"
    assert results.json()["scores"]["metric_deviations"] is not None
    assert len(results.json()["scores"]["phase_scores"]) == 3
    assert history.json()[0]["upload_id"] == upload_id


def test_annotated_video_is_regenerated_when_file_is_missing(
    client: TestClient,
    workflow_storage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = register(client)
    upload_response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Running"},
        files={"file": ("run.mp4", b"video-content", "video/mp4")},
    )
    upload_id = upload_response.json()["upload_id"]
    monkeypatch.setattr(
        "app.services.mediapipe_pose.MediaPipePoseService.extract_all",
        lambda self, video_path: extracted_pose(),
    )
    monkeypatch.setattr(
        "app.services.video_quality.VideoQualityService.validate",
        lambda self, pose, sport: VideoQualityResult(
            valid=True,
            reasons=[],
            detected_frames=1,
            full_body_frames=1,
        ),
    )

    processing = client.post(
        f"/api/v1/videos/{upload_id}/process", headers=headers
    )
    assert processing.status_code == 200, processing.text
    for path in settings.annotated_video_directory.rglob("*.mp4"):
        path.unlink()

    response = client.get(
        f"/api/v1/videos/{upload_id}/annotated-content", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.content == b"annotated-video"


def test_biomechanics_requires_completed_pose_processing(
    client: TestClient, workflow_storage: None
) -> None:
    headers = register(client)
    upload_response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Running"},
        files={"file": ("run.mp4", b"video-content", "video/mp4")},
    )

    response = client.post(
        f"/api/v1/videos/{upload_response.json()['upload_id']}/biomechanics",
        headers=headers,
    )

    assert response.status_code == 409


def test_running_gait_metrics_are_not_added_to_non_running_uploads(
    client: TestClient,
    workflow_storage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = register(client)
    upload_response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Jumping"},
        files={"file": ("jump.mp4", b"video-content", "video/mp4")},
    )
    upload_id = upload_response.json()["upload_id"]
    monkeypatch.setattr(
        "app.services.mediapipe_pose.MediaPipePoseService.extract_all",
        lambda self, video_path: extracted_pose(),
    )
    monkeypatch.setattr(
        "app.services.video_quality.VideoQualityService.validate",
        lambda self, pose, sport: VideoQualityResult(
            valid=True,
            reasons=[],
            detected_frames=1,
            full_body_frames=1,
        ),
    )

    processing = client.post(
        f"/api/v1/videos/{upload_id}/process", headers=headers
    )
    biomechanics = client.post(
        f"/api/v1/videos/{upload_id}/biomechanics", headers=headers
    )

    assert processing.status_code == 200, processing.text
    assert biomechanics.status_code == 200, biomechanics.text
    assert biomechanics.json()["running"] is None
