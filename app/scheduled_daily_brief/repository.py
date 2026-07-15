from __future__ import annotations

from typing import Protocol

from google.cloud import firestore

from app.scheduled_daily_brief.models import ScheduledDailyBriefRun, utc_now


CONFIRMED_STATUSES = {"draft_created", "delivered"}


class ScheduledBriefRepository(Protocol):
    def acquire(self, run: ScheduledDailyBriefRun) -> tuple[ScheduledDailyBriefRun, bool]:
        pass

    def get(self, idempotency_key: str) -> ScheduledDailyBriefRun | None:
        pass

    def mark_running(self, run: ScheduledDailyBriefRun) -> ScheduledDailyBriefRun:
        pass

    def mark_skipped(self, run: ScheduledDailyBriefRun, *, reason: str | None = None) -> ScheduledDailyBriefRun:
        pass

    def mark_draft_created(self, run: ScheduledDailyBriefRun, *, brief_id: str, delivery_id: str) -> ScheduledDailyBriefRun:
        pass

    def mark_delivered(self, run: ScheduledDailyBriefRun, *, brief_id: str, delivery_id: str) -> ScheduledDailyBriefRun:
        pass

    def mark_failed(self, run: ScheduledDailyBriefRun, *, error_code: str, error_summary: str) -> ScheduledDailyBriefRun:
        pass

    def mark_blocked(self, run: ScheduledDailyBriefRun, *, error_code: str, error_summary: str) -> ScheduledDailyBriefRun:
        pass

    def list_recent(self, limit: int = 10) -> list[ScheduledDailyBriefRun]:
        pass


class InMemoryScheduledBriefRepository:
    def __init__(self) -> None:
        self.runs: dict[str, ScheduledDailyBriefRun] = {}

    def acquire(self, run: ScheduledDailyBriefRun) -> tuple[ScheduledDailyBriefRun, bool]:
        existing = self.runs.get(run.idempotency_key)
        if existing:
            return existing, False
        self.runs[run.idempotency_key] = run
        return run, True

    def get(self, idempotency_key: str) -> ScheduledDailyBriefRun | None:
        return self.runs.get(idempotency_key)

    def mark_running(self, run: ScheduledDailyBriefRun) -> ScheduledDailyBriefRun:
        return self._save(run.with_updates(status="running"))

    def mark_skipped(self, run: ScheduledDailyBriefRun, *, reason: str | None = None) -> ScheduledDailyBriefRun:
        return self._finish(run, status="skipped", error_code=run.error_code, error_summary=reason or run.error_summary)

    def mark_draft_created(self, run: ScheduledDailyBriefRun, *, brief_id: str, delivery_id: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="draft_created", brief_id=brief_id, delivery_id=delivery_id)

    def mark_delivered(self, run: ScheduledDailyBriefRun, *, brief_id: str, delivery_id: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="delivered", brief_id=brief_id, delivery_id=delivery_id)

    def mark_failed(self, run: ScheduledDailyBriefRun, *, error_code: str, error_summary: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="failed", error_code=error_code, error_summary=error_summary)

    def mark_blocked(self, run: ScheduledDailyBriefRun, *, error_code: str, error_summary: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="blocked", error_code=error_code, error_summary=error_summary)

    def list_recent(self, limit: int = 10) -> list[ScheduledDailyBriefRun]:
        return sorted(self.runs.values(), key=lambda item: item.started_at, reverse=True)[:limit]

    def _save(self, run: ScheduledDailyBriefRun) -> ScheduledDailyBriefRun:
        self.runs[run.idempotency_key] = run
        return run

    def _finish(self, run: ScheduledDailyBriefRun, **updates) -> ScheduledDailyBriefRun:
        finished_at = utc_now()
        updates.setdefault("finished_at", finished_at)
        updates.setdefault("duration_seconds", _duration(run.started_at, finished_at))
        return self._save(run.with_updates(**updates))


class FirestoreScheduledBriefRepository:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)
        self.collection = self.client.collection("scheduled_daily_brief_runs")

    def acquire(self, run: ScheduledDailyBriefRun) -> tuple[ScheduledDailyBriefRun, bool]:
        doc_ref = self.collection.document(run.idempotency_key)
        transaction = self.client.transaction()

        @firestore.transactional
        def _acquire(tx):
            snapshot = doc_ref.get(transaction=tx)
            if snapshot.exists:
                return ScheduledDailyBriefRun(**(snapshot.to_dict() or {})), False
            tx.set(doc_ref, run.to_dict())
            return run, True

        return _acquire(transaction)

    def get(self, idempotency_key: str) -> ScheduledDailyBriefRun | None:
        snapshot = self.collection.document(idempotency_key).get()
        if not snapshot.exists:
            return None
        return ScheduledDailyBriefRun(**(snapshot.to_dict() or {}))

    def mark_running(self, run: ScheduledDailyBriefRun) -> ScheduledDailyBriefRun:
        return self._save(run.with_updates(status="running"))

    def mark_skipped(self, run: ScheduledDailyBriefRun, *, reason: str | None = None) -> ScheduledDailyBriefRun:
        return self._finish(run, status="skipped", error_summary=reason or run.error_summary)

    def mark_draft_created(self, run: ScheduledDailyBriefRun, *, brief_id: str, delivery_id: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="draft_created", brief_id=brief_id, delivery_id=delivery_id)

    def mark_delivered(self, run: ScheduledDailyBriefRun, *, brief_id: str, delivery_id: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="delivered", brief_id=brief_id, delivery_id=delivery_id)

    def mark_failed(self, run: ScheduledDailyBriefRun, *, error_code: str, error_summary: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="failed", error_code=error_code, error_summary=error_summary)

    def mark_blocked(self, run: ScheduledDailyBriefRun, *, error_code: str, error_summary: str) -> ScheduledDailyBriefRun:
        return self._finish(run, status="blocked", error_code=error_code, error_summary=error_summary)

    def list_recent(self, limit: int = 10) -> list[ScheduledDailyBriefRun]:
        docs = self.collection.order_by("started_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [ScheduledDailyBriefRun(**(doc.to_dict() or {})) for doc in docs]

    def _save(self, run: ScheduledDailyBriefRun) -> ScheduledDailyBriefRun:
        self.collection.document(run.idempotency_key).set(run.to_dict(), merge=True)
        return run

    def _finish(self, run: ScheduledDailyBriefRun, **updates) -> ScheduledDailyBriefRun:
        finished_at = utc_now()
        updates.setdefault("finished_at", finished_at)
        updates.setdefault("duration_seconds", _duration(run.started_at, finished_at))
        return self._save(run.with_updates(**updates))


def _duration(started_at: str, finished_at: str) -> float:
    start = _parse(started_at)
    finish = _parse(finished_at)
    return round((finish - start).total_seconds(), 3)


def _parse(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
