import asyncio
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.assessment import Assessment
from app.models.video import VideoUpload
from app.utils.config import settings
from tests.conftest import TestSessionFactory


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Assessment Athlete",
            "email": email,
            "password": "secure-password-123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/videos/upload",
        headers=headers,
        data={"sport": "Bowling"},
        files={"file": ("bowl.mp4", b"video-content", "video/mp4")},
    )
    assert response.status_code == 201
    return response.json()["upload_id"]


def score_payload(score: float) -> dict[str, float]:
    return {
        "technique_score": score,
        "efficiency_score": score,
        "balance_score": score,
        "overall_score": score,
    }


async def load_saved(upload_id: str) -> tuple[Assessment, VideoUpload]:
    async with TestSessionFactory() as session:
        assessment_result = await session.execute(
            select(Assessment).where(
                Assessment.upload_id == uuid.UUID(upload_id)
            )
        )
        upload_result = await session.execute(
            select(VideoUpload).where(VideoUpload.id == uuid.UUID(upload_id))
        )
        assessment = assessment_result.scalar_one()
        video_upload = upload_result.scalar_one()
        session.expunge(assessment)
        session.expunge(video_upload)
        return assessment, video_upload


@pytest.fixture
def upload_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(settings, "upload_directory", tmp_path)
    return tmp_path


def test_stores_rule_based_assessment_and_completes_upload(
    client: TestClient, upload_directory: Path
) -> None:
    headers = register(client, "assessment@example.com")
    upload_id = upload(client, headers)

    response = client.post(
        f"/api/v1/videos/{upload_id}/assessment",
        headers=headers,
        json=score_payload(45),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strengths"] == []
    assert len(body["weaknesses"]) == 3
    assert len(body["improvement_suggestions"]) == 3

    assessment, stored_upload = asyncio.run(load_saved(upload_id))
    assert assessment.weaknesses == body["weaknesses"]
    assert assessment.improvement_suggestions == body["improvement_suggestions"]
    assert stored_upload.status == "Completed"

    detail_response = client.get(
        f"/api/v1/videos/{upload_id}/results", headers=headers
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["video"]["filename"] == "bowl.mp4"
    assert detail_response.json()["scores"]["overall_score"] == 45

    history_response = client.get("/api/v1/videos/history", headers=headers)
    assert history_response.status_code == 200
    assert history_response.json()[0]["upload_id"] == upload_id
    assert history_response.json()[0]["overall_score"] == 45

    video_response = client.get(
        f"/api/v1/videos/{upload_id}/content", headers=headers
    )
    assert video_response.status_code == 200
    assert video_response.content == b"video-content"


def test_repeated_assessment_updates_single_record(
    client: TestClient, upload_directory: Path
) -> None:
    headers = register(client, "repeat@example.com")
    upload_id = upload(client, headers)
    endpoint = f"/api/v1/videos/{upload_id}/assessment"

    client.post(endpoint, headers=headers, json=score_payload(45))
    response = client.post(endpoint, headers=headers, json=score_payload(90))

    assert response.status_code == 200
    assessment, _ = asyncio.run(load_saved(upload_id))
    assert len(assessment.strengths) == 3
    assert assessment.weaknesses == []


def test_assessment_requires_authentication(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/videos/{uuid.uuid4()}/assessment",
        json=score_payload(80),
    )

    assert response.status_code == 401


def test_user_cannot_assess_another_athletes_upload(
    client: TestClient, upload_directory: Path
) -> None:
    owner_headers = register(client, "assessment-owner@example.com")
    other_headers = register(client, "assessment-other@example.com")
    upload_id = upload(client, owner_headers)

    response = client.post(
        f"/api/v1/videos/{upload_id}/assessment",
        headers=other_headers,
        json=score_payload(80),
    )

    assert response.status_code == 404
