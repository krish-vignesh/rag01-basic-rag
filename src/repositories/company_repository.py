
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.orm import Company


class CompanyRepository:
    def get_by_id(
        self,
        session: Session,
        company_id: UUID,
    ) -> Company | None:
        statement = select(Company).where(
            Company.company_id == company_id
        )

        return session.scalars(statement).one_or_none()

    def create(
        self,
        session: Session,
        company_name: str,
    ) -> Company:
        company = Company(company_name=company_name)

        session.add(company)
        session.flush()

        return company
