
from sqlalchemy import select
#Select is used to construct SQL SELECT statements in a more Pythonic way, allowing for easier querying of the database using SQLAlchemy's ORM capabilities.
from sqlalchemy.orm import Session

from src.models.orm import File


class FileRepository:
    def get_by_id(
        self,
        session: Session,
        file_id: str,
    ) -> File | None:
        statement = select(File).where(
            File.file_id == file_id
        )

        return session.scalars(statement).one_or_none()

    def create(
        self,
        session: Session,
        file_id: str,
    ) -> File:
        file_record = File(file_id=file_id)

        session.add(file_record)
        session.flush()

        return file_record
