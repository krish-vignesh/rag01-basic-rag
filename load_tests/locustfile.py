"""Locust scenario for isolated RAG01 document-ingestion environments.

Run with:
    uv run --active locust -f load_tests/locustfile.py

Set ``RAG01_COMPANY_ID`` and optionally ``RAG01_AUTH_TOKEN``. The target
host can be supplied with Locust's ``--host`` option or ``RAG01_BASE_URL``.
"""

import os
from uuid import uuid4

from locust import HttpUser, between, task


class RAG01DocumentUser(HttpUser):
    """Upload unique small documents through the single-document endpoint."""

    host = os.getenv("RAG01_BASE_URL", "http://localhost:8000")
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.company_id = os.getenv("RAG01_COMPANY_ID")
        if not self.company_id:
            raise RuntimeError("RAG01_COMPANY_ID must be configured.")
        self.auth_token = os.getenv("RAG01_AUTH_TOKEN")

    @task
    def upload_document(self) -> None:
        filename = f"locust-{uuid4().hex}.txt"
        content = f"RAG01 load-test document {uuid4()}".encode()
        headers = (
            {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        )

        with self.client.post(
            "/documents",
            data={"company_id": self.company_id},
            files={"file": (filename, content, "text/plain")},
            headers=headers,
            name="/documents",
            catch_response=True,
        ) as response:
            if response.status_code not in {201}:
                response.failure(
                    f"document upload returned HTTP {response.status_code}"
                )
