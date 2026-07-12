from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.athlete_profile import AthleteProfile
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate


class ProfileNotFoundError(ValueError):
    pass


class ProfileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user: User) -> ProfileResponse:
        profile = await self._find(user.id)
        if profile is None:
            raise ProfileNotFoundError
        return self._response(user, profile)

    async def update(self, user: User, payload: ProfileUpdate) -> ProfileResponse:
        profile = await self._find(user.id)
        user.name = payload.name

        if profile is None:
            profile = AthleteProfile(user_id=user.id)
            self.session.add(profile)

        profile.age = payload.age
        profile.gender = payload.gender
        profile.state = payload.state
        profile.sport = payload.sport
        profile.experience = payload.experience

        await self.session.commit()
        await self.session.refresh(user)
        await self.session.refresh(profile)
        return self._response(user, profile)

    async def _find(self, user_id) -> AthleteProfile | None:
        result = await self.session.execute(
            select(AthleteProfile).where(AthleteProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _response(user: User, profile: AthleteProfile) -> ProfileResponse:
        return ProfileResponse(
            name=user.name,
            age=profile.age,
            gender=profile.gender,
            state=profile.state,
            sport=profile.sport,
            experience=profile.experience,
        )
