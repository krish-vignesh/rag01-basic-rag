
from sqlalchemy import select

from src.database import SessionFactory
from src.models.orm import File
from src.repositories.file_repository import FileRepository


repository = FileRepository()

# A test-only value; this is not a real file hash.
test_hash = "a" * 64

with SessionFactory.begin() as session:
    try:
        # Test creating a file identity.
        created = repository.create(session, test_hash)
        print("Created:", created.file_id == test_hash)

        # Test looking up the identity.
        found = repository.get_by_id(session, test_hash)
        print("Found:", found is not None)
        print("Hash matches:", found.file_id == test_hash)

        # Test a hash that does not exist.
        missing = repository.get_by_id(session, "b" * 64)
        print("Missing hash returns None:", missing is None)

    finally:
        # Discard the test insertion instead of committing it.
        session.rollback()

# Verify the test record was not persisted.
with SessionFactory() as session:
    remaining = session.scalars(
        select(File).where(File.file_id == test_hash)
    ).one_or_none()

    print("Test record removed by rollback:", remaining is None)
