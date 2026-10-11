
from sqlalchemy import select
from uuid import UUID
from src.database import SessionFactory
from src.models.orm import Company
from src.repositories.company_repository import CompanyRepository


repository = CompanyRepository()
test_name = "RAG01 Repository Test Company"

with SessionFactory.begin() as session:
    try:
        # Create a company.
        created = repository.create(session, test_name)
        company_id = created.company_id

        print("Created:", created.company_name == test_name)
        print("Generated UUID:", company_id is not None)

        # Retrieve the company using its UUID.
        found = repository.get_by_id(session, company_id)

        print("Found:", found is not None)
        print("Name matches:", found.company_name == test_name)

        # Test an unknown UUID.
        missing = repository.get_by_id(
            session,
            UUID("00000000-0000-0000-0000-000000000001"),
        )

        print("Missing company returns None:", missing is None)

    finally:
        session.rollback()

# Verify the test company was not persisted.
with SessionFactory() as session:
    remaining = session.scalars(
        select(Company).where(Company.company_id == company_id)
    ).one_or_none()

    print("Test record removed by rollback:", remaining is None)
