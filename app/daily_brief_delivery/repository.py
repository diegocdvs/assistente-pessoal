from __future__ import annotations

from typing import Protocol

from google.cloud import firestore

from app.daily_brief_delivery.models import DailyBriefDeliveryRecord


class DailyBriefDeliveryRepository(Protocol):
    def save(self, record: DailyBriefDeliveryRecord) -> str:
        pass

    def find_by_idempotency_key(self, idempotency_key: str) -> DailyBriefDeliveryRecord | None:
        pass


class InMemoryDailyBriefDeliveryRepository:
    def __init__(self) -> None:
        self.records: dict[str, DailyBriefDeliveryRecord] = {}

    def save(self, record: DailyBriefDeliveryRecord) -> str:
        self.records[record.delivery_id] = record
        return record.delivery_id

    def find_by_idempotency_key(self, idempotency_key: str) -> DailyBriefDeliveryRecord | None:
        for record in self.records.values():
            if record.idempotency_key == idempotency_key:
                return record
        return None


class FirestoreDailyBriefDeliveryRepository:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def save(self, record: DailyBriefDeliveryRecord) -> str:
        self.client.collection("daily_brief_deliveries").document(record.delivery_id).set(record.to_dict(), merge=True)
        return record.delivery_id

    def find_by_idempotency_key(self, idempotency_key: str) -> DailyBriefDeliveryRecord | None:
        docs = list(
            self.client.collection("daily_brief_deliveries")
            .where("idempotency_key", "==", idempotency_key)
            .limit(1)
            .stream()
        )
        if not docs:
            return None
        return DailyBriefDeliveryRecord(**(docs[0].to_dict() or {}))
