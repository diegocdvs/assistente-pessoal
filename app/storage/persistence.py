from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from app.core.models import ActionPlan, Classification, EmailEntity


@dataclass(frozen=True)
class PersistenceResult:
    document_id: str
    existed: bool


class FirestorePersistence:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def save_run(self, report: dict[str, Any]) -> str:
        doc_ref = self.client.collection("runs").document()
        doc_ref.set({**report, "created_at": _now()})
        return doc_ref.id

    def save_email(self, email: EmailEntity) -> PersistenceResult:
        doc_ref = self._account_document(email.account_id).collection("emails").document(_safe_document_id(email.id))
        snapshot = doc_ref.get()
        existed = bool(getattr(snapshot, "exists", False))

        payload = {
            **email.to_dict(),
            "last_seen_at": _now(),
        }
        if not existed:
            payload["first_seen_at"] = _now()

        doc_ref.set(payload, merge=True)
        return PersistenceResult(document_id=doc_ref.id, existed=existed)

    def save_classification(self, email: EmailEntity, classification: Classification) -> str:
        doc_ref = self._account_document(email.account_id).collection("classifications").document(_safe_document_id(email.id))
        doc_ref.set(
            {
                "message_id": email.id,
                "account_id": email.account_id,
                "provider": email.provider,
                **classification.to_dict(),
                "updated_at": _now(),
            },
            merge=True,
        )
        return doc_ref.id

    def save_action_plan(self, email: EmailEntity, action_plan: ActionPlan) -> str:
        doc_ref = self._account_document(email.account_id).collection("action_plans").document(_safe_document_id(email.id))
        doc_ref.set(
            {
                "message_id": email.id,
                "account_id": email.account_id,
                "provider": email.provider,
                f"plans.{action_plan.type}": action_plan.to_dict(),
                "updated_at": _now(),
            },
            merge=True,
        )
        return doc_ref.id

    def upsert_email(
        self,
        email: EmailEntity,
        classification: Classification,
        action_plans: list[ActionPlan],
    ) -> PersistenceResult:
        result = self.save_email(email)
        self.save_classification(email, classification)
        for action_plan in action_plans:
            self.save_action_plan(email, action_plan)
        return result

    def _account_document(self, account_id: str):
        return self.client.collection("accounts").document(account_id)


def _safe_document_id(value: str) -> str:
    return value.replace("/", "_")


def _now() -> datetime:
    return datetime.now(timezone.utc)
