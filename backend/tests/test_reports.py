import asyncio
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.assessment import Assessment
from app.utils.config import settings
from tests.conftest import TestSessionFactory
from tests.test_authority import register, seed_authority_data


async def upload_id_for_assessment(assessment_id: str) -> str:
    async with TestSessionFactory() as session:
        result = await session.execute(
            select(Assessment).where(Assessment.id == uuid.UUID(assessment_id))
        )
        return str(result.scalar_one().upload_id)


@pytest.fixture
def report_setup(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, str]:
    monkeypatch.setattr(
        settings, "annotated_video_directory", tmp_path / "annotated_videos"
    )
    authority_id, authority_token = register(
        client, "report-authority@example.com", "Report Reviewer"
    )
    athlete_id, athlete_token = register(
        client, "report-athlete@example.com", "Report Athlete"
    )
    assessment_id, _, _ = asyncio.run(
        seed_authority_data(authority_id, athlete_id, tmp_path)
    )
    upload_id = asyncio.run(upload_id_for_assessment(str(assessment_id)))
    return {
        "authority": f"Bearer {authority_token}",
        "athlete": f"Bearer {athlete_token}",
        "assessment_id": str(assessment_id),
        "upload_id": upload_id,
    }


def assert_pdf_response(response) -> None:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 3000


def test_athlete_downloads_own_assessment_report(
    client: TestClient, report_setup: dict[str, str]
) -> None:
    response = client.get(
        f"/api/v1/videos/{report_setup['upload_id']}/report",
        headers={"Authorization": report_setup["athlete"]},
    )

    assert_pdf_response(response)
    assert "report-athlete" in response.headers["content-disposition"]


def test_authority_downloads_assessment_report(
    client: TestClient, report_setup: dict[str, str]
) -> None:
    response = client.get(
        f"/api/v1/authority/assessments/{report_setup['assessment_id']}/report",
        headers={"Authorization": report_setup["authority"]},
    )

    assert_pdf_response(response)


def test_report_downloads_enforce_scope_and_roles(
    client: TestClient, report_setup: dict[str, str]
) -> None:
    other_id, other_token = register(
        client, "other-report-athlete@example.com", "Other Athlete"
    )
    assert other_id
    athlete_response = client.get(
        f"/api/v1/videos/{report_setup['upload_id']}/report",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    authority_response = client.get(
        f"/api/v1/authority/assessments/{report_setup['assessment_id']}/report",
        headers={"Authorization": report_setup["athlete"]},
    )

    assert athlete_response.status_code == 404
    assert authority_response.status_code == 403
