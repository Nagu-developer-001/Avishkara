import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.athlete_profile import AthleteProfile
from app.models.user import User
from app.models.video import VideoUpload
from app.utils.security import hash_password
from tests.conftest import TestSessionFactory


def score_payload(overall: float) -> dict:
    return {
        "technique_score": overall,
        "efficiency_score": overall,
        "balance_score": overall,
        "overall_score": overall,
        "metric_deviations": None,
        "phase_scores": [],
    }


async def seed_leaderboard() -> str:
    now = datetime.now(UTC)
    current_email = "ranked-athlete@example.com"
    async with TestSessionFactory() as session:
        for index, score in enumerate([100, 90, 80, 70, 60, 50, 40]):
            athlete_id = uuid.uuid4()
            upload_id = uuid.uuid4()
            session.add(
                User(
                    id=athlete_id,
                    name=(
                        "Current Athlete"
                        if index == 6
                        else f"Leaderboard Athlete {index + 1}"
                    ),
                    email=current_email if index == 6 else f"leader-{index}@example.com",
                    hashed_password=hash_password("secure-password-123"),
                )
            )
            session.add(
                AthleteProfile(
                    user_id=athlete_id,
                    age=18 + index,
                    gender="Male" if index == 1 else "Female",
                    state="Kerala" if index == 1 else "Karnataka",
                    sport="Cricket Bowling" if index == 1 else "Running",
                    experience=6 if index == 1 else 2,
                )
            )
            session.add(
                VideoUpload(
                    id=upload_id,
                    athlete_id=athlete_id,
                    sport="Cricket Bowling" if index == 1 else "Running",
                    filename=f"run-{index}.mp4",
                    upload_time=now + timedelta(minutes=index),
                    status="Completed",
                    content_type="video/mp4",
                    file_size_bytes=100,
                    temporary_path=f"run-{index}.mp4",
                )
            )
            session.add(
                Assessment(
                    upload_id=upload_id,
                    strengths=[],
                    weaknesses=[],
                    improvement_suggestions=[],
                )
            )
            session.add(
                AssessmentSnapshot(
                    upload_id=upload_id,
                    benchmark_result=score_payload(score),
                )
            )
        await session.commit()
    return current_email


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "secure-password-123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_leaderboard_returns_top_five_and_current_rank_when_outside_top_five(
    client: TestClient,
) -> None:
    email = asyncio.run(seed_leaderboard())

    response = client.get("/api/v1/videos/leaderboard", headers=login(client, email))

    assert response.status_code == 200, response.text
    body = response.json()
    assert [entry["rank"] for entry in body["top_athletes"]] == [1, 2, 3, 4, 5]
    assert [entry["overall_score"] for entry in body["top_athletes"]] == [
        100,
        90,
        80,
        70,
        60,
    ]
    assert body["current_user_entry"]["rank"] == 7
    assert body["current_user_entry"]["overall_score"] == 40
    assert body["current_user_entry"]["is_current_user"] is True


def test_leaderboard_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/videos/leaderboard")

    assert response.status_code == 401


def test_leaderboard_filters_by_profile_and_sport(client: TestClient) -> None:
    email = asyncio.run(seed_leaderboard())

    response = client.get(
        "/api/v1/videos/leaderboard",
        headers=login(client, email),
        params={
            "sport": "Cricket Bowling",
            "gender": "Male",
            "state": "Kerala",
            "min_age": 19,
            "max_age": 19,
            "min_experience": 6,
            "max_experience": 6,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["top_athletes"]) == 1
    assert body["top_athletes"][0]["name"] == "Leaderboard Athlete 2"
    assert body["top_athletes"][0]["sport"] == "Cricket Bowling"
    assert body["current_user_entry"] is None

    alias_response = client.get(
        "/api/v1/videos/leaderboard",
        headers=login(client, email),
        params={
            "sport": "Bowling",
            "gender": "Male",
            "state": "Kerala",
            "min_age": 19,
            "max_age": 19,
            "min_experience": 6,
            "max_experience": 6,
        },
    )

    assert alias_response.status_code == 200, alias_response.text
    alias_body = alias_response.json()
    assert len(alias_body["top_athletes"]) == 1
    assert alias_body["top_athletes"][0]["name"] == "Leaderboard Athlete 2"
