import argparse
import asyncio

from sqlalchemy import select

from app.database.session import SessionFactory, initialize_database
from app.models.authority_role import AuthorityRole
from app.models.user import User


async def grant(email: str) -> None:
    await initialize_database()
    async with SessionFactory() as session:
        result = await session.execute(
            select(User).where(User.email == email.strip().lower())
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise SystemExit("Register the user before granting authority access.")
        existing = await session.execute(
            select(AuthorityRole).where(AuthorityRole.user_id == user.id)
        )
        if existing.scalar_one_or_none() is None:
            session.add(AuthorityRole(user_id=user.id))
            await session.commit()
        print(f"Authority access granted to {user.email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    arguments = parser.parse_args()
    asyncio.run(grant(arguments.email))
