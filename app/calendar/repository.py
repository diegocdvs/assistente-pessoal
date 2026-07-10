from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from google.cloud import firestore

from app.calendar.models import CalendarEvent, DailyAgenda


@dataclass(frozen=True)
class CalendarPersistenceResult:
    document_id: str
    existed: bool


class CalendarRepository(Protocol):
    def upsert_event(self, event: CalendarEvent) -> CalendarPersistenceResult:
        pass

    def list_events(self, *, account_id: str | None = None, limit: int = 100) -> list[CalendarEvent]:
        pass

    def save_daily_agenda(self, agenda: DailyAgenda) -> str:
        pass


class InMemoryCalendarRepository:
    def __init__(self, events: list[CalendarEvent] | None = None) -> None:
        self.events = {(event.account_id, event.id): event for event in events or []}
        self.agendas: dict[str, DailyAgenda] = {}

    def upsert_event(self, event: CalendarEvent) -> CalendarPersistenceResult:
        key = (event.account_id, event.id)
        existed = key in self.events
        self.events[key] = event
        return CalendarPersistenceResult(document_id=event.id, existed=existed)

    def list_events(self, *, account_id: str | None = None, limit: int = 100) -> list[CalendarEvent]:
        values = list(self.events.values())
        if account_id:
            values = [event for event in values if event.account_id == account_id]
        return sorted(values, key=lambda event: event.start_at)[:limit]

    def save_daily_agenda(self, agenda: DailyAgenda) -> str:
        self.agendas[agenda.date] = agenda
        return agenda.date


class FirestoreCalendarRepository:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def upsert_event(self, event: CalendarEvent) -> CalendarPersistenceResult:
        doc_ref = self.client.collection("accounts").document(event.account_id).collection("calendar_events").document(
            _safe_document_id(event.id)
        )
        snapshot = doc_ref.get()
        existed = bool(getattr(snapshot, "exists", False))
        payload: dict[str, Any] = {**event.to_dict(), "last_seen_at": _now()}
        if not existed:
            payload["first_seen_at"] = _now()
        doc_ref.set(payload, merge=True)
        return CalendarPersistenceResult(document_id=doc_ref.id, existed=existed)

    def list_events(self, *, account_id: str | None = None, limit: int = 100) -> list[CalendarEvent]:
        docs = []
        if account_id:
            docs = list(self.client.collection("accounts").document(account_id).collection("calendar_events").limit(limit).stream())
        else:
            for account_doc in self.client.collection("accounts").stream():
                docs.extend(account_doc.reference.collection("calendar_events").limit(limit).stream())
        return [CalendarEvent(**payload) for doc in docs if (payload := doc.to_dict() or {})]

    def save_daily_agenda(self, agenda: DailyAgenda) -> str:
        self.client.collection("daily_agendas").document(agenda.date).set(agenda.to_dict(), merge=True)
        return agenda.date


def _safe_document_id(value: str) -> str:
    return value.replace("/", "_")


def _now() -> datetime:
    return datetime.now(timezone.utc)
