from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.security import hash_password, verify_password


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, payload: RegisterRequest) -> User:
        normalized_email = payload.email.lower()
        result = await self.session.execute(
            select(User).where(User.email == normalized_email)
        )
        if result.scalar_one_or_none():
            raise EmailAlreadyRegisteredError

        user = User(
            name=payload.name.strip(),
            email=normalized_email,
            hashed_password=hash_password(payload.password),
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise EmailAlreadyRegisteredError from exc
        await self.session.refresh(user)
        return user

    async def authenticate(self, payload: LoginRequest) -> User:
        result = await self.session.execute(
            select(User).where(User.email == payload.email.lower())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError
        return user
