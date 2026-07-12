import asyncio
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.video import VideoUpload
from app.utils.config import settings
from tests.conftest import TestSessionFactory


def auth_details(client: TestClient) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Arjun Rao",
            "email": "video@example.com",
            "password": "secure-password-123",
        },
    )
    body = response.json()
    return (
        {"Authorization": f"Bearer {body['access_token']}"},
        body["user"]["id"],
    )


async def load_upload(upload_id: str) -> VideoUpload:
    async with TestSessionFactory() as session:
        result = await session.execute(
            select(VideoUpload).where(VideoUpload.id == uuid.UUID(upload_id))
        )
        upload = result.scalar_one()
        session.expunge(upload)
        return upload


@pytest.fixture
def upload_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(settings, "upload_directory", tmp_path)
    return tmp_path


def test_upload_stores_file_and_metadata(
    client: TestClient,
    upload_directory: Path,
) -> None:
    headers, athlete_id = auth_details(client)
    content = b"mock-video-content"

    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Jumping"},
        files={"file": ("jump.mp4", content, "video/mp4")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "Uploaded"
    assert uuid.UUID(body["upload_id"])

    upload = asyncio.run(load_upload(body["upload_id"]))
    assert str(upload.athlete_id) == athlete_id
    assert upload.sport == "Jumping"
    assert upload.filename == "jump.mp4"
    assert upload.status == "Uploaded"
    assert upload.upload_time is not None
    assert upload.file_size_bytes == len(content)
    assert Path(upload.temporary_path).read_bytes() == content
    assert Path(upload.temporary_path).is_relative_to(upload_directory)


def test_upload_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/videos/upload",
        data={"sport": "Running"},
        files={"file": ("run.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 401


def test_upload_rejects_unsupported_file(client: TestClient) -> None:
    headers, _ = auth_details(client)
    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Running"},
        files={"file": ("notes.txt", b"not-a-video", "text/plain")},
    )

    assert response.status_code == 415


def test_upload_rejects_empty_file(
    client: TestClient,
    upload_directory: Path,
) -> None:
    headers, _ = auth_details(client)
    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Bowling"},
        files={"file": ("bowl.mp4", b"", "video/mp4")},
    )

    assert response.status_code == 400
    assert list(upload_directory.rglob("*.mp4")) == []


def test_upload_enforces_streamed_size_limit(
    client: TestClient,
    upload_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.video_storage.MAX_VIDEO_SIZE_BYTES", 5)
    headers, _ = auth_details(client)
    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Running"},
        files={"file": ("run.mp4", b"123456", "video/mp4")},
    )

    assert response.status_code == 413
    assert list(upload_directory.rglob("*.mp4")) == []


def test_upload_validates_sport(client: TestClient) -> None:
    headers, _ = auth_details(client)
    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Swimming"},
        files={"file": ("swim.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 422
