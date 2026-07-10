from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.models import SCHEMA_VERSION


BRIEF_STATUSES = {"OK", "WARNING", "ERROR"}


@dataclass(frozen=True)
class DailyBriefSection:
    key: str
    title: str
    priority: int
    status: str
    items: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    count: int = 0
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in BRIEF_STATUSES:
            raise ValueError(f"Status invalido para secao: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyBrief:
    brief_id: str
    date: str
    timezone: str
    generated_at: str
    account_ids: list[str]
    status: str
    headline: str
    agenda_today: list[dict[str, Any]]
    agenda_tomorrow: list[dict[str, Any]]
    next_event: dict[str, Any] | None
    free_windows_today: list[dict[str, Any]]
    calendar_conflicts: list[dict[str, Any]]
    critical_emails: list[dict[str, Any]]
    top_priorities: list[dict[str, Any]]
    followups: list[dict[str, Any]]
    pending_action_plans: list[dict[str, Any]]
    subscriptions_recommended: list[dict[str, Any]]
    subscriptions_waiting_approval: int
    security_warnings: list[dict[str, Any]]
    high_risk_items: list[dict[str, Any]]
    last_audit_status: str
    last_audit_at: str | None
    open_discrepancies: list[dict[str, Any]]
    summary_metrics: dict[str, int]
    sections: list[DailyBriefSection]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status not in BRIEF_STATUSES:
            raise ValueError(f"Status invalido para brief: {self.status}")

    @classmethod
    def empty(cls, *, date: str, timezone_name: str, account_ids: list[str] | None = None) -> "DailyBrief":
        generated_at = datetime.now(timezone.utc).isoformat()
        return cls(
            brief_id=f"daily-brief:{date}:{','.join(account_ids or ['all'])}",
            date=date,
            timezone=timezone_name,
            generated_at=generated_at,
            account_ids=account_ids or [],
            status="OK",
            headline="Dia tranquilo: nenhuma pendencia critica.",
            agenda_today=[],
            agenda_tomorrow=[],
            next_event=None,
            free_windows_today=[],
            calendar_conflicts=[],
            critical_emails=[],
            top_priorities=[],
            followups=[],
            pending_action_plans=[],
            subscriptions_recommended=[],
            subscriptions_waiting_approval=0,
            security_warnings=[],
            high_risk_items=[],
            last_audit_status="unknown",
            last_audit_at=None,
            open_discrepancies=[],
            summary_metrics={},
            sections=[],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "date": self.date,
            "timezone": self.timezone,
            "generated_at": self.generated_at,
            "account_ids": list(self.account_ids),
            "status": self.status,
            "headline": self.headline,
            "agenda_today": list(self.agenda_today),
            "agenda_tomorrow": list(self.agenda_tomorrow),
            "next_event": self.next_event,
            "free_windows_today": list(self.free_windows_today),
            "calendar_conflicts": list(self.calendar_conflicts),
            "critical_emails": list(self.critical_emails),
            "top_priorities": list(self.top_priorities),
            "followups": list(self.followups),
            "pending_action_plans": list(self.pending_action_plans),
            "subscriptions_recommended": list(self.subscriptions_recommended),
            "subscriptions_waiting_approval": self.subscriptions_waiting_approval,
            "security_warnings": list(self.security_warnings),
            "high_risk_items": list(self.high_risk_items),
            "last_audit_status": self.last_audit_status,
            "last_audit_at": self.last_audit_at,
            "open_discrepancies": list(self.open_discrepancies),
            "summary_metrics": dict(self.summary_metrics),
            "sections": [section.to_dict() for section in sorted(self.sections, key=lambda item: item.priority)],
            "schema_version": self.schema_version,
        }
