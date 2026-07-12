import asyncio
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.athlete_profile import AthleteProfile
from app.models.authority_role import AuthorityRole
from app.models.shortlist import AthleteShortlist
from app.models.video import VideoUpload
from app.utils.config import settings
from tests.conftest import TestSessionFactory


def register(client: TestClient, email: str, name: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "secure-password-123"},
    )
    body = response.json()
    return body["user"]["id"], body["access_token"]


async def seed_authority_data(
    authority_id: str, athlete_id: str, tmp_path: Path
) -> tuple[uuid.UUID, Path, Path]:
    upload_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    original = tmp_path / "athlete.mp4"
    original.write_bytes(b"original-video")
    annotated = (
        settings.annotated_video_directory / athlete_id / f"{upload_id}.mp4"
    )
    annotated.parent.mkdir(parents=True, exist_ok=True)
    annotated.write_bytes(b"annotated-video")
    async with TestSessionFactory() as session:
        session.add(AuthorityRole(user_id=uuid.UUID(authority_id)))
        session.add(
            AthleteProfile(
                user_id=uuid.UUID(athlete_id),
                age=19,
                gender="Female",
                state="Karnataka",
                sport="Running",
                experience=4,
            )
        )
        session.add(
            VideoUpload(
                id=upload_id,
                athlete_id=uuid.UUID(athlete_id),
                sport="Running",
                filename="athlete.mp4",
                status="Completed",
                content_type="video/mp4",
                file_size_bytes=14,
                temporary_path=str(original),
            )
        )
        session.add(
            Assessment(
                id=assessment_id,
                upload_id=upload_id,
                strengths=["Stable landing"],
                weaknesses=["Stride consistency"],
                improvement_suggestions=["Maintain cadence"],
            )
        )
        session.add(
            AssessmentSnapshot(
                upload_id=upload_id,
                benchmark_result={
                    "technique_score": 82,
                    "efficiency_score": 76,
                    "balance_score": 88,
                    "overall_score": 81.4,
                    "metric_deviations": None,
                    "phase_scores": [],
                },
            )
        )
        await session.commit()
    return assessment_id, original, annotated


@pytest.fixture
def authority_setup(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, str]:
    monkeypatch.setattr(
        settings, "annotated_video_directory", tmp_path / "annotated_videos"
    )
    monkeypatch.setattr(
        "app.services.video_processing.VideoProcessingService._is_readable_video",
        staticmethod(lambda path: Path(path).is_file() and Path(path).stat().st_size > 0),
    )
    authority_id, authority_token = register(
        client, "authority@example.com", "National Reviewer"
    )
    athlete_id, athlete_token = register(
        client, "athlete-authority@example.com", "Talent Athlete"
    )
    assessment_id, _, _ = asyncio.run(
        seed_authority_data(authority_id, athlete_id, tmp_path)
    )
    return {
        "authority": f"Bearer {authority_token}",
        "athlete": f"Bearer {athlete_token}",
        "assessment_id": str(assessment_id),
        "athlete_id": athlete_id,
    }


def test_authority_dashboard_totals_filters_and_access_control(
    client: TestClient, authority_setup: dict[str, str]
) -> None:
    athlete_response = client.get(
        "/api/v1/authority/dashboard",
        headers={"Authorization": authority_setup["athlete"]},
    )
    assert athlete_response.status_code == 403

    authority_session = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": authority_setup["authority"]},
    )
    assert authority_session.status_code == 200
    assert authority_session.json()["role"] == "authority"

    response = client.get(
        "/api/v1/authority/dashboard?sport=Running&state=Karnataka&min_age=18&max_score=90",
        headers={"Authorization": authority_setup["authority"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {
        "total_athletes": 1,
        "total_assessments": 1,
        "average_overall_score": 81.4,
    }
    assert len(body["recent_assessments"]) == 1
    assert body["athletes"][0]["name"] == "Talent Athlete"
    assert body["athletes"][0]["latest_score"] == 81.4
    assert body["athletes"][0]["shortlisted"] is False


def test_authority_reviews_videos_and_shortlists_an_athlete(
    client: TestClient, authority_setup: dict[str, str]
) -> None:
    assessment_id = authority_setup["assessment_id"]
    headers = {"Authorization": authority_setup["authority"]}

    detail = client.get(
        f"/api/v1/authority/assessments/{assessment_id}", headers=headers
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["athlete"]["state"] == "Karnataka"
    assert body["scores"]["technique_score"] == 82
    assert body["recommendations"]["strengths"] == ["Stable landing"]
    assert body["video"]["annotated_available"] is True

    original = client.get(
        f"/api/v1/authority/assessments/{assessment_id}/video", headers=headers
    )
    annotated = client.get(
        f"/api/v1/authority/assessments/{assessment_id}/annotated-video",
        headers=headers,
    )
    assert original.content == b"original-video"
    assert annotated.content == b"annotated-video"

    shortlist = client.post(
        f"/api/v1/authority/assessments/{assessment_id}/shortlist",
        headers=headers,
        json={"remarks": "Invite for national trials"},
    )
    assert shortlist.status_code == 200, shortlist.text
    assert shortlist.json()["athlete_id"] == authority_setup["athlete_id"]
    assert shortlist.json()["remarks"] == "Invite for national trials"

    filtered = client.get(
        "/api/v1/authority/dashboard?shortlisted=true", headers=headers
    )
    assert len(filtered.json()["athletes"]) == 1
    assert filtered.json()["athletes"][0]["shortlisted"] is True

    async def count_shortlists() -> int:
        async with TestSessionFactory() as session:
            from sqlalchemy import select

            result = await session.execute(select(AthleteShortlist))
            return len(result.scalars().all())

    assert asyncio.run(count_shortlists()) == 1
