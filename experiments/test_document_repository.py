
from uuid import uuid4

from src.database import SessionFactory
from src.models.orm import Company, File, Document
from src.repositories.company_repository import CompanyRepository
from src.repositories.file_repository import FileRepository
from src.repositories.document_repository import DocumentRepository


company_repository = CompanyRepository()
file_repository = FileRepository()
document_repository = DocumentRepository()


class RollbackTestComplete(Exception):
    """Force rollback after verifying repository behavior."""


def run_test():
    company_id = None
    file_id = uuid4().hex * 2
    document_id = uuid4()

    try:
        with SessionFactory.begin() as session:
            # 1. Create the prerequisite company and file identity.
            company = company_repository.create(
                session,
                company_name=f"Test Company {uuid4()}",
            )
            company_id = company.company_id

            file_record = file_repository.create(session, file_id)
            session.flush()

            # 2. Create the document using an explicit UUID.
            created = document_repository.create(
                session=session,
                document_id=document_id,
                company_id=company_id,
                file_id=file_id,
                filename="test_document.pdf",
                file_type="pdf",
                blob_name=f"{company_id}/{document_id}/test_document.pdf",
            )

            print("Document created:", created.document_id == document_id)
            print("Initial status is pending:", created.status == "pending")

            # 3. Retrieve by document ID.
            found = document_repository.get_by_id(session, document_id)
            print("Document found:", found is not None)
            print("Filename matches:", found.filename == "test_document.pdf")

            # 4. Update status.
            updated = document_repository.update_status(
                session,
                document_id,
                "processing",
            )
            print("Status updated:", updated.status == "processing")

            # 5. Verify missing document behavior.
            missing_id = uuid4()
            missing = document_repository.get_by_id(session, missing_id)
            print("Missing document returns None:", missing is None)

            missing_update = document_repository.update_status(
                session,
                missing_id,
                "processing",
            )
            print("Missing document update returns None:", missing_update is None)

            # 6. Test lookup by company ID + file hash.
            match = document_repository.get_by_company_and_file(
                session,
                company_id,
                file_id,
            )
            print("Company and file match:", match is not None)
            print("Correct document found:", match.document_id == document_id)

            # 7. A different company must not match.
            different_company = document_repository.get_by_company_and_file(
                session,
                uuid4(),
                file_id,
            )
            print(
                "Different company returns None:",
                different_company is None,
            )

            # 8. A different hash must not match.
            different_file = document_repository.get_by_company_and_file(
                session,
                company_id,
                "a" * 64,
            )
            print(
                "Different file hash returns None:",
                different_file is None,
            )

            # Force rollback of all test inserts and updates.
            raise RollbackTestComplete

    except RollbackTestComplete:
        print("Test transaction rolled back.")

    # 9. Verify the records did not persist after rollback.
    with SessionFactory() as session:
        remaining_document = document_repository.get_by_id(
            session,
            document_id,
        )
        remaining_company = company_repository.get_by_id(
            session,
            company_id,
        )
        remaining_file = file_repository.get_by_id(
            session,
            file_id,
        )

        print("Document removed by rollback:", remaining_document is None)
        print("Company removed by rollback:", remaining_company is None)
        print("File identity removed by rollback:", remaining_file is None)


if __name__ == "__main__":
    run_test()
