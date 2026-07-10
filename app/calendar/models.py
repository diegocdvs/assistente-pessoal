from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.models import SCHEMA_VERSION, WorkItem


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    provider: str
    account_id: str
    calendar_id: str
    title: str
    description_summary: str | None
    location: str | None
    start_at: str
    end_at: str
    timezone: str | None
    all_day: bool
    status: str
    organizer: str | None
    attendees: list[str] = field(default_factory=list)
    attendee_count: int = 0
    user_response_status: str | None = None
    recurrence_id: str | None = None
    recurring: bool = False
    meeting_url_present: bool = False
    visibility: str | None = None
    source_updated_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_work_item(self) -> WorkItem:
        return WorkItem(
            id=f"{self.provider}:calendar:{self.id}",
            source=self.provider,
            type="calendar_event",
            account_id=self.account_id,
            payload=self.to_dict(),
            created_at=self.start_at,
        )


@dataclass(frozen=True)
class CalendarListEntry:
    id: str
    provider: str
    account_id: str
    summary: str
    timezone: str | None = None
    primary: bool = False
    access_role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class FreeWindow:
    start_at: str
    end_at: str
    duration_minutes: int

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class CalendarConflict:
    type: str
    severity: str
    event_ids: list[str]
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class MeetingContext:
    calendar_event_id: str
    title: str
    starts_at: str
    minutes_until_start: int | None
    participants: list[str]
    related_emails: list[dict[str, Any]] = field(default_factory=list)
    related_work_items: list[dict[str, Any]] = field(default_factory=list)
    related_action_plans: list[dict[str, Any]] = field(default_factory=list)
    security_warnings: list[dict[str, Any]] = field(default_factory=list)
    preparation_notes: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyAgenda:
    date: str
    timezone: str
    events_today: list[dict[str, Any]]
    next_event: dict[str, Any] | None
    all_day_events: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    free_windows: list[dict[str, Any]]
    critical_emails: list[dict[str, Any]]
    followups: list[dict[str, Any]]
    pending_action_plans: list[dict[str, Any]]
    subscriptions_waiting_approval: int
    security_warnings: list[dict[str, Any]]
    double_check_status: str
    top_priorities: list[dict[str, Any]]
    summary_lines: list[str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
