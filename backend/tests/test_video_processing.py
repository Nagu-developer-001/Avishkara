import asyncio
import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.pose_processing import PoseProcessingResult
from app.models.video import VideoUpload
from app.schemas.pose import (
    FullVideoPoseResult,
    PoseLandmark,
    ProcessedPoseFrame,
)
from app.utils.config import settings
from app.schemas.video_quality import VideoQualityResult
from tests.conftest import TestSessionFactory


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test Athlete",
            "email": email,
            "password": "secure-password-123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Running"},
        files={"file": ("run.mp4", b"video-content", "video/mp4")},
    )
    assert response.status_code == 201
    return response.json()["upload_id"]


def pose_result() -> FullVideoPoseResult:
    landmarks = [
        PoseLandmark(
            index=index,
            name=f"landmark_{index}",
            x=index / 100,
            y=index / 100,
            z=0,
            visibility=0.9,
            presence=0.9,
        )
        for index in range(33)
    ]
    return FullVideoPoseResult(
        fps=30,
        total_frames=2,
        processed_frames=2,
        frames=[
            ProcessedPoseFrame(
                frame_index=0, timestamp_ms=0, landmarks=landmarks
            ),
            ProcessedPoseFrame(
                frame_index=1, timestamp_ms=33, landmarks=[]
            ),
        ],
    )


async def load_processing_result(upload_id: str) -> PoseProcessingResult:
    async with TestSessionFactory() as session:
        result = await session.execute(
            select(PoseProcessingResult).where(
                PoseProcessingResult.upload_id == uuid.UUID(upload_id)
            )
        )
        stored = result.scalar_one()
        session.expunge(stored)
        return stored


async def load_video_upload(upload_id: str) -> VideoUpload:
    async with TestSessionFactory() as session:
        result = await session.execute(
            select(VideoUpload).where(VideoUpload.id == uuid.UUID(upload_id))
        )
        stored = result.scalar_one()
        session.expunge(stored)
        return stored


@pytest.fixture
def storage_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, Path]:
    upload_directory = tmp_path / "uploads"
    landmark_directory = tmp_path / "landmarks"
    monkeypatch.setattr(settings, "upload_directory", upload_directory)
    monkeypatch.setattr(settings, "landmark_directory", landmark_directory)
    monkeypatch.setattr(
        settings, "annotated_video_directory", tmp_path / "annotated_videos"
    )
    monkeypatch.setattr(
        "app.services.video_processing.VideoProcessingService._is_readable_video",
        staticmethod(lambda path: Path(path).is_file() and Path(path).stat().st_size > 0),
    )
    return upload_directory, landmark_directory


def test_processes_upload_and_saves_landmarks(
    client: TestClient,
    storage_directories: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = register(client, "processing@example.com")
    upload_id = upload(client, headers)
    monkeypatch.setattr(
        "app.services.mediapipe_pose.MediaPipePoseService.extract_all",
        lambda self, video_path: pose_result(),
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
    monkeypatch.setattr(
        "app.services.biomechanical_visualization.BiomechanicalVisualizationService.generate",
        lambda self, video_path, pose_result, output_path: (
            output_path.parent.mkdir(parents=True, exist_ok=True),
            output_path.write_bytes(b"annotated-video"),
            output_path,
        )[-1],
    )

    response = client.post(
        f"/api/v1/videos/{upload_id}/process", headers=headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["uploadId"] == upload_id
    assert body["totalFrames"] == 2
    assert body["processedFrames"] == 2

    landmark_path = Path(body["landmarkFile"])
    payload = json.loads(landmark_path.read_text(encoding="utf-8"))
    assert payload["uploadId"] == upload_id
    assert len(payload["frames"]) == 2
    assert len(payload["frames"][0]["landmarks"]) == 33
    assert payload["frames"][1]["landmarks"] == []

    stored = asyncio.run(load_processing_result(upload_id))
    assert stored.total_frames == 2
    assert stored.processed_frames == 2
    assert stored.landmark_file == str(landmark_path)

    response = client.get(
        f"/api/v1/videos/{upload_id}/annotated-content", headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"annotated-video"
    assert response.headers["content-type"] == "video/mp4"


def test_annotated_video_requires_authentication(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/videos/{uuid.uuid4()}/annotated-content"
    )

    assert response.status_code == 401


def test_processing_requires_authentication(client: TestClient) -> None:
    response = client.post(f"/api/v1/videos/{uuid.uuid4()}/process")

    assert response.status_code == 401


def test_rejects_an_unusable_video_before_biomechanics(
    client: TestClient,
    storage_directories: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = register(client, "rejected-video@example.com")
    upload_response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Bowling"},
        files={"file": ("cropped.mp4", b"video-content", "video/mp4")},
    )
    upload_id = upload_response.json()["upload_id"]
    monkeypatch.setattr(
        "app.services.mediapipe_pose.MediaPipePoseService.extract_all",
        lambda self, video_path: pose_result(),
    )
    monkeypatch.setattr(
        "app.services.video_quality.VideoQualityService.validate",
        lambda self, pose, sport: VideoQualityResult(
            valid=False,
            reasons=["Keep the athlete's complete body visible."],
            detected_frames=2,
            full_body_frames=0,
        ),
    )

    response = client.post(
        f"/api/v1/videos/{upload_id}/process", headers=headers
    )

    assert response.status_code == 422
    assert "complete body" in response.json()["detail"]
    assert asyncio.run(load_video_upload(upload_id)).status == "Rejected"


def test_user_cannot_process_another_athletes_upload(
    client: TestClient,
    storage_directories: tuple[Path, Path],
) -> None:
    owner_headers = register(client, "owner@example.com")
    other_headers = register(client, "other@example.com")
    upload_id = upload(client, owner_headers)

    response = client.post(
        f"/api/v1/videos/{upload_id}/process", headers=other_headers
    )

    assert response.status_code == 404
