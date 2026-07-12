from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.utils.config import settings

connect_args = (
    {"ssl": "require"}
    if settings.database_ssl
    and settings.database_url.startswith("postgresql+asyncpg://")
    else {}
)
engine = create_async_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session


async def initialize_database() -> None:
    from app.models.assessment import Assessment  # noqa: F401
    from app.models.assessment_snapshot import AssessmentSnapshot  # noqa: F401
    from app.models.athlete_profile import AthleteProfile  # noqa: F401
    from app.models.authority_role import AuthorityRole  # noqa: F401
    from app.models.pose_processing import PoseProcessingResult  # noqa: F401
    from app.models.shortlist import AthleteShortlist  # noqa: F401
    from app.models.user import User  # noqa: F401
    from app.models.video import VideoUpload  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
