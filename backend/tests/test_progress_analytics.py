import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.user import User
from app.models.video import VideoUpload
from app.utils.security import hash_password
from tests.conftest import TestSessionFactory


def score_payload(
    *, technique: float, efficiency: float, balance: float, overall: float
) -> dict:
    return {
        "technique_score": technique,
        "efficiency_score": efficiency,
        "balance_score": balance,
        "overall_score": overall,
        "metric_deviations": None,
        "phase_scores": [],
    }


async def seed_progress() -> tuple[str, uuid.UUID]:
    athlete_id = uuid.uuid4()
    other_athlete_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with TestSessionFactory() as session:
        session.add_all(
            [
                User(
                    id=athlete_id,
                    name="Progress Athlete",
                    email="progress@example.com",
                    hashed_password=hash_password("secure-password-123"),
                ),
                User(
                    id=other_athlete_id,
                    name="Other Athlete",
                    email="other-progress@example.com",
                    hashed_password="unused",
                ),
            ]
        )
        for index, scores in enumerate(
            [
                score_payload(technique=50, efficiency=60, balance=70, overall=60),
                score_payload(technique=70, efficiency=75, balance=80, overall=75),
                score_payload(technique=85, efficiency=80, balance=90, overall=85),
            ]
        ):
            upload_id = uuid.uuid4()
            session.add(
                VideoUpload(
                    id=upload_id,
                    athlete_id=athlete_id,
                    sport="Running",
                    filename=f"run-{index}.mp4",
                    upload_time=now + timedelta(days=index),
                    status="Completed",
                    content_type="video/mp4",
                    file_size_bytes=100,
                    temporary_path=f"run-{index}.mp4",
                )
            )
            session.add(
                AssessmentSnapshot(upload_id=upload_id, benchmark_result=scores)
            )

        other_upload_id = uuid.uuid4()
        session.add(
            VideoUpload(
                id=other_upload_id,
                athlete_id=other_athlete_id,
                sport="Jumping",
                filename="other.mp4",
                upload_time=now,
                status="Completed",
                content_type="video/mp4",
                file_size_bytes=100,
                temporary_path="other.mp4",
            )
        )
        session.add(
            AssessmentSnapshot(
                upload_id=other_upload_id,
                benchmark_result=score_payload(
                    technique=100, efficiency=100, balance=100, overall=100
                ),
            )
        )
        await session.commit()
    return "progress@example.com", athlete_id


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "secure-password-123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_returns_progress_from_the_authenticated_athletes_history(
    client: TestClient,
) -> None:
    email, _ = asyncio.run(seed_progress())

    response = client.get(
        "/api/v1/videos/analytics/progress", headers=login(client, email)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assessment_count"] == 3
    assert body["average_score"] == pytest.approx(73.33, abs=0.01)
    assert body["best_score"] == 85
    assert body["improvement"] == 25
    assert [point["overall_score"] for point in body["trend"]] == [60, 75, 85]
    assert [point["technique_score"] for point in body["trend"]] == [50, 70, 85]


def test_progress_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/videos/analytics/progress")

    assert response.status_code == 401
