from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm_legacy import Company


class CompanyRepository:
    async def get_by_id(
        self,
        session: AsyncSession,
        company_id: UUID,
    ) -> Company | None:
        statement = select(Company).where(Company.company_id == company_id)

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        company_name: str,
    ) -> Company:
        company = Company(company_name=company_name)

        session.add(company)
        await session.flush()

        return company
