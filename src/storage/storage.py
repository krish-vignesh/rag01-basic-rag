from pathlib import Path
import shutil


class LocalStorage:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save( #Saves the file to the local storage, creating necessary directories if they don't exist. Raises a FileExistsError if the file already exists.
        self,
        source_file: str,
        company_id: str,
        document_id: str,
        filename: str
    ) -> Path:

        document_path = (
            self.base_path
            / company_id
            / document_id
        )

        document_path.mkdir(parents=True, exist_ok=True)

        destination = document_path / filename

        if self.exists(
            company_id=company_id,
            document_id=document_id,
            filename=filename
        ):
            raise FileExistsError(
                f"File '{destination}' already exists. Please choose a different filename or document_id."
            )

        shutil.copy2(source_file, destination)

        return destination

    def exists( #Says if the file exists or not
    self,
    company_id: str,
    document_id: str,
    filename: str
) -> bool:

        destination = (
            self.base_path
            / company_id
            / document_id
            / filename
        )

        return destination.exists()

    def get(  # To locate the file path to ingestion layer then pdf load finds the file
            self,
            company_id: str,
            document_id: str,
            filename: str
    ) -> Path:

        destination = (
            self.base_path
            / company_id
            / document_id
            / filename
        )

        if not self.exists(
            company_id=company_id,
            document_id=document_id,
            filename=filename
        ):
            raise FileNotFoundError(
                f"File '{destination}' does not exist."
            )

        return destination

    def list(
            self,
            company_id: str,
    ) -> list[dict]: #function expected to return a list of dictionaries
        company_path = self.base_path / company_id

        if not company_path.exists():
            return []

        documents = []

        for document_id in company_path.iterdir():
            if document_id.is_dir():

                files = list(document_id.iterdir())

                if files:
                    file_path = files[0]

                    documents.append({
                        "filename": file_path.name,
                        "created_at": file_path.stat().st_ctime
                    })

        return documents

    def delete(
    self,
    company_id: str,
    document_id: str,
    filename: str
) -> None:

        destination = (
            self.base_path
            / company_id
            / document_id
            / filename
        )

        if not destination.exists():
            raise FileNotFoundError(
                f"File '{destination}' does not exist."
            )

        destination.unlink()