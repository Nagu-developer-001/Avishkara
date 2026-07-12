from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./avishkara.db"
    database_ssl: bool = False
    jwt_secret_key: str = Field(
        default="development-only-change-this-secret-before-deployment",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0, le=10080)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    cors_origin_regex: str | None = (
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    )
    pose_landmarker_model_path: Path = (
        Path(__file__).resolve().parents[2]
        / "models"
        / "pose_landmarker_lite.task"
    )
    upload_directory: Path = Path(__file__).resolve().parents[2] / "uploads"
    landmark_directory: Path = Path(__file__).resolve().parents[2] / "landmarks"
    annotated_video_directory: Path = (
        Path(__file__).resolve().parents[2] / "annotated_videos"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
