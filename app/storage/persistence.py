from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from app.core.models import ActionPlan, Classification, EmailEntity


@dataclass(frozen=True)
class PersistenceResult:
    email_id: str
    existed: bool


class FirestorePersistence:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def save_run(self, report: dict[str, Any]) -> str:
        doc_ref = self.client.collection("runs").document()
        doc_ref.set({**report, "created_at": _now()})
        return doc_ref.id

    def upsert_email(
        self,
        email: EmailEntity,
        classification: Classification,
        actions: list[ActionPlan],
    ) -> PersistenceResult:
        doc_ref = self._email_document(email)
        snapshot = doc_ref.get()
        existed = bool(getattr(snapshot, "exists", False))

        payload = {
            **email.to_dict(),
            "last_seen_at": _now(),
            "classification": classification.to_dict(),
            "actions": [action.to_dict() for action in actions],
        }
        if not existed:
            payload["first_seen_at"] = _now()

        doc_ref.set(payload, merge=True)
        return PersistenceResult(email_id=email.id, existed=existed)

    def _email_document(self, email: EmailEntity):
        return (
            self.client.collection("accounts")
            .document(email.account_id)
            .collection("emails")
            .document(_safe_document_id(email.id))
        )


def _safe_document_id(value: str) -> str:
    return value.replace("/", "_")


def _now() -> datetime:
    return datetime.now(timezone.utc)
