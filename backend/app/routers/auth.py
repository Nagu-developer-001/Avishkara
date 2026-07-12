from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_database_session
from app.models.authority_role import AuthorityRole
from app.models.user import User
from app.routers.dependencies import get_current_user
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    SessionResponse,
    UserResponse,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from app.utils.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.get("/me", response_model=SessionResponse)
async def current_session(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> SessionResponse:
    result = await session.execute(
        select(AuthorityRole.id).where(AuthorityRole.user_id == current_user.id)
    )
    role = "authority" if result.scalar_one_or_none() else "athlete"
    return SessionResponse(
        user=UserResponse.model_validate(current_user),
        role=role,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_database_session),
) -> AuthResponse:
    try:
        user = await AuthService(session).register(payload)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc

    return AuthResponse(
        access_token=create_access_token(str(user.id)),
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_database_session),
) -> AuthResponse:
    try:
        user = await AuthService(session).authenticate(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return AuthResponse(
        access_token=create_access_token(str(user.id)),
        user=UserResponse.model_validate(user),
    )
