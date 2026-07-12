from app.utils.config import Settings


def test_normalizes_supabase_postgres_url_for_asyncpg() -> None:
    settings = Settings(
        database_url=(
            "postgresql://postgres.project:password@"
            "aws-0-region.pooler.supabase.com:5432/postgres"
        ),
        _env_file=None,
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_preserves_sqlite_url() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///./test.db",
        _env_file=None,
    )

    assert settings.database_url == "sqlite+aiosqlite:///./test.db"
