from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CalendarDiscrepancy:
    type: str
    severity: str
    event_id: str | None = None
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CalendarDoubleCheck:
    def inspect(
        self,
        *,
        source_events: list[dict[str, Any]],
        persisted_events: list[dict[str, Any]],
        context_snapshot: dict[str, Any] | None = None,
        conflicts: list[dict[str, Any]] | None = None,
    ) -> list[CalendarDiscrepancy]:
        discrepancies: list[CalendarDiscrepancy] = []
        persisted_by_id = {event.get("id"): event for event in persisted_events}
        seen: set[str] = set()
        for event in source_events:
            if event.get("id") not in persisted_by_id:
                discrepancies.append(CalendarDiscrepancy("source_event_missing_in_persistence", "error", event.get("id")))
        for event in persisted_events:
            event_id = str(event.get("id"))
            if event_id in seen:
                discrepancies.append(CalendarDiscrepancy("duplicate_calendar_event", "error", event_id))
            seen.add(event_id)
            if not event.get("schema_version"):
                discrepancies.append(CalendarDiscrepancy("calendar_event_missing_schema_version", "warning", event_id))
            if event.get("provider") != "google_calendar":
                discrepancies.append(CalendarDiscrepancy("calendar_event_provider_incorrect", "warning", event_id))
            if event.get("metadata", {}).get("security_required") and not event.get("metadata", {}).get("security_assessment_id"):
                discrepancies.append(CalendarDiscrepancy("security_assessment_missing", "warning", event_id))
        if context_snapshot is not None:
            expected = len(persisted_events)
            actual = int(context_snapshot.get("calendar_events_upcoming") or 0)
            if actual > expected:
                discrepancies.append(CalendarDiscrepancy("calendar_context_count_mismatch", "warning", evidence={"expected": expected, "actual": actual}))
        if conflicts is not None and any(conflict.get("type") == "overlap" for conflict in conflicts) is False and _has_overlap(persisted_events):
            discrepancies.append(CalendarDiscrepancy("calendar_conflict_not_detected", "warning"))
        return discrepancies


def _has_overlap(events: list[dict[str, Any]]) -> bool:
    timed = sorted([event for event in events if not event.get("all_day")], key=lambda event: event.get("start_at", ""))
    return any(timed[index].get("end_at") > timed[index + 1].get("start_at") for index in range(len(timed) - 1))
