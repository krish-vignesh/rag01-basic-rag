
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.user import User


class UserRepository:
    async def get_by_keycloak_sub(
        self,
        session: AsyncSession,
        keycloak_sub: str,
    ) -> User | None:
        statement = select(User).where(
            User.keycloak_sub == keycloak_sub
        )

        result = await session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> User | None:
        statement = select(User).where(
            User.user_id == user_id
        )

        result = await session.execute(statement)

        return result.scalar_one_or_none()
