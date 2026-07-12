from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import initialize_database
from app.routers.auth import router as auth_router
from app.routers.authority import router as authority_router
from app.routers.analysis import router as analysis_router
from app.routers.profile import router as profile_router
from app.routers.videos import router as videos_router
from app.utils.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_database()
    yield

app = FastAPI(
    title="Avishkara Biomechanics API",
    version="0.1.0",
    description=(
        "Explainable, physics-based sports movement analysis. "
        "No language model is used for scoring."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(authority_router)
app.include_router(profile_router)
app.include_router(videos_router)
app.include_router(analysis_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "Avishkara API"}
