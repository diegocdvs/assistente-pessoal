from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore


class FirestoreStore:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def save_run(self, report: dict[str, Any]) -> str:
        doc_ref = self.client.collection("runs").document()
        payload = {
            **report,
            "created_at": datetime.now(timezone.utc),
        }
        doc_ref.set(payload)
        return doc_ref.id
