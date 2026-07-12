import asyncio
import os
from collections.abc import AsyncGenerator, Generator

os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-with-at-least-32-characters"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test-lifespan.db"
os.environ["DATABASE_SSL"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_database_session
from app.main import app

test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    poolclass=StaticPool,
)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_database_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session


async def reset_database() -> None:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    asyncio.run(reset_database())
    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
