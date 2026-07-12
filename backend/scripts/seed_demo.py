import asyncio
import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select

from app.database.session import SessionFactory, initialize_database
from app.models.assessment import Assessment
from app.models.assessment_snapshot import AssessmentSnapshot
from app.models.athlete_profile import AthleteProfile
from app.models.authority_role import AuthorityRole
from app.models.user import User
from app.models.video import VideoUpload
from app.utils.config import settings
from app.utils.security import hash_password


DEMO_PASSWORD = "Demo@2026"
ATHLETE_EMAIL = "athlete@demo.com"
AUTHORITY_EMAIL = "authority@demo.com"

ASSESSMENTS = (
    ("demo-running-01.mp4", 72.0, 68.0, 75.0, 71.7, 21),
    ("demo-running-02.mp4", 78.0, 74.0, 81.0, 77.7, 14),
    ("demo-running-03.mp4", 86.0, 82.0, 89.0, 85.7, 7),
)


def render_demo_video(path: Path, *, annotated: bool, score: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"avc1"), 24, (640, 360)
    )
    if not writer.isOpened():
        raise RuntimeError("Unable to create the demo video")
    for frame_index in range(72):
        image = np.zeros((360, 640, 3), dtype=np.uint8)
        image[:] = (14, 20, 30)
        x = 90 + frame_index * 6
        bounce = int(10 * math.sin(frame_index / 5))
        hip = (x, 190 + bounce)
        shoulder = (x, 125 + bounce)
        head = (x, 92 + bounce)
        left_knee = (x - 28, 250 + bounce)
        right_knee = (x + 34, 245 + bounce)
        left_ankle = (x - 55, 310)
        right_ankle = (x + 65, 310)
        left_elbow = (x - 35, 155 + bounce)
        right_elbow = (x + 38, 150 + bounce)
        left_wrist = (x - 62, 185 + bounce)
        right_wrist = (x + 65, 178 + bounce)
        color = (40, 225, 180) if annotated else (220, 230, 240)
        for start, end in (
            (head, shoulder), (shoulder, hip),
            (shoulder, left_elbow), (left_elbow, left_wrist),
            (shoulder, right_elbow), (right_elbow, right_wrist),
            (hip, left_knee), (left_knee, left_ankle),
            (hip, right_knee), (right_knee, right_ankle),
        ):
            cv2.line(image, start, end, color, 5, cv2.LINE_AA)
        cv2.circle(image, head, 18, color, 4, cv2.LINE_AA)
        if annotated:
            for point in (shoulder, hip, left_knee, right_knee, left_elbow, right_elbow):
                cv2.circle(image, point, 7, (40, 80, 255), -1, cv2.LINE_AA)
            cv2.putText(image, "KNEE 164.2 deg", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(image, "HIP 171.8 deg", (24, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(image, "ELBOW 88.6 deg", (24, 102), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, f"AVISHKARA DEMO  |  SCORE {score:.1f}", (330, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 220, 80), 2, cv2.LINE_AA)
        writer.write(image)
    writer.release()


async def upsert_user(session, *, email: str, name: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(name=name, email=email, hashed_password=hash_password(DEMO_PASSWORD))
        session.add(user)
        await session.flush()
    else:
        user.name = name
        user.hashed_password = hash_password(DEMO_PASSWORD)
    return user


async def seed() -> None:
    await initialize_database()
    async with SessionFactory() as session:
        athlete = await upsert_user(
            session, email=ATHLETE_EMAIL, name="Aarav Demo Athlete"
        )
        authority = await upsert_user(
            session, email=AUTHORITY_EMAIL, name="National Talent Reviewer"
        )
        role_result = await session.execute(
            select(AuthorityRole).where(AuthorityRole.user_id == authority.id)
        )
        if role_result.scalar_one_or_none() is None:
            session.add(AuthorityRole(user_id=authority.id))

        profile_result = await session.execute(
            select(AthleteProfile).where(AthleteProfile.user_id == athlete.id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            profile = AthleteProfile(user_id=athlete.id)
            session.add(profile)
        profile.age = 19
        profile.gender = "Male"
        profile.state = "Karnataka"
        profile.sport = "Running"
        profile.experience = 4

        now = datetime.now(UTC)
        for filename, technique, efficiency, balance, overall, days_ago in ASSESSMENTS:
            upload_result = await session.execute(
                select(VideoUpload).where(
                    VideoUpload.athlete_id == athlete.id,
                    VideoUpload.filename == filename,
                )
            )
            upload = upload_result.scalar_one_or_none()
            if upload is None:
                upload = VideoUpload(
                    athlete_id=athlete.id,
                    sport="Running",
                    filename=filename,
                    upload_time=now - timedelta(days=days_ago),
                    status="Completed",
                    content_type="video/mp4",
                    file_size_bytes=0,
                    temporary_path="",
                )
                session.add(upload)
                await session.flush()

            original_path = settings.upload_directory / str(athlete.id) / f"{upload.id}.mp4"
            annotated_path = settings.annotated_video_directory / str(athlete.id) / f"{upload.id}.mp4"
            if not original_path.is_file():
                render_demo_video(original_path, annotated=False, score=overall)
            if not annotated_path.is_file():
                render_demo_video(annotated_path, annotated=True, score=overall)
            upload.temporary_path = str(original_path)
            upload.file_size_bytes = original_path.stat().st_size
            upload.status = "Completed"

            assessment_result = await session.execute(
                select(Assessment).where(Assessment.upload_id == upload.id)
            )
            assessment = assessment_result.scalar_one_or_none()
            if assessment is None:
                assessment = Assessment(upload_id=upload.id)
                session.add(assessment)
            assessment.strengths = ["Strong bilateral balance", "Consistent running posture"]
            assessment.weaknesses = ["Stride efficiency can improve"]
            assessment.improvement_suggestions = ["Maintain cadence while increasing hip extension"]

            snapshot_result = await session.execute(
                select(AssessmentSnapshot).where(
                    AssessmentSnapshot.upload_id == upload.id
                )
            )
            snapshot = snapshot_result.scalar_one_or_none()
            if snapshot is None:
                snapshot = AssessmentSnapshot(upload_id=upload.id)
                session.add(snapshot)
            snapshot.benchmark_result = {
                "technique_score": technique,
                "efficiency_score": efficiency,
                "balance_score": balance,
                "overall_score": overall,
                "metric_deviations": None,
                "phase_scores": [],
            }

        await session.commit()

    print("Demo environment ready")
    print(f"Athlete:   {ATHLETE_EMAIL} / {DEMO_PASSWORD}")
    print(f"Authority: {AUTHORITY_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
