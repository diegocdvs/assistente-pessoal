from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from app.core.models import ProcessedEmail


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

    def save_processed_email(self, processed: ProcessedEmail) -> str:
        doc_id = self._processed_email_id(
            processed.email.account_id,
            processed.email.provider,
            processed.email.id,
        )
        payload = {
            **processed.to_dict(),
            "updated_at": datetime.now(timezone.utc),
        }
        self.client.collection("processed_emails").document(doc_id).set(payload, merge=True)
        return doc_id

    def save_processed_emails(self, processed: list[ProcessedEmail]) -> list[str]:
        if not processed:
            return []
        batch = self.client.batch()
        ids: list[str] = []
        for item in processed:
            doc_id = self._processed_email_id(item.email.account_id, item.email.provider, item.email.id)
            ids.append(doc_id)
            ref = self.client.collection("processed_emails").document(doc_id)
            batch.set(ref, {**item.to_dict(), "updated_at": datetime.now(timezone.utc)}, merge=True)
        batch.commit()
        return ids

    def _processed_email_id(self, account_id: str, provider: str, message_id: str) -> str:
        return f"{account_id}_{provider}_{message_id}".replace("/", "_")
