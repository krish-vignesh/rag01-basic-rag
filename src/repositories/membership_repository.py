
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.company_membership import CompanyMembership


class MembershipRepository:
    async def get_active_by_user_id(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> CompanyMembership | None:
        statement = select(CompanyMembership).where(
            CompanyMembership.user_id == user_id,
            CompanyMembership.status == "ACTIVE",
        )

        result = await session.execute(statement)

        return result.scalar_one_or_none()
