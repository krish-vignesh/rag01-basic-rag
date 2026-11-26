
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.platform_admin import PlatformAdmin


class PlatformAdminRepository:
    async def get_active_by_user_id(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> PlatformAdmin | None:
        statement = select(PlatformAdmin).where(
            PlatformAdmin.user_id == user_id,
            PlatformAdmin.status == "ACTIVE",
        )

        result = await session.execute(statement)

        return result.scalar_one_or_none()
