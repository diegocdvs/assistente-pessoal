from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.models import SCHEMA_VERSION


@dataclass(frozen=True)
class FollowUpSuggestion:
    id: str
    type: str
    reason: str
    account_id: str
    work_item_id: str | None = None
    email_id: str | None = None
    thread_id: str | None = None
    age_days: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class RankedWorkItem:
    work_item: dict[str, Any]
    score: int
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_item": self.work_item,
            "score": self.score,
            "reasons": list(self.reasons),
            "schema_version": SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class OperationalSummary:
    total_emails: int
    critical_emails: int
    followups: int
    pending_action_plans: int
    top_category: str | None
    top_priority: str | None
    total_by_category: dict[str, int]
    total_by_priority: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class ContextSnapshot:
    date: str
    generated_at: str
    window_days: int
    emails_pending: list[dict[str, Any]]
    emails_critical: list[dict[str, Any]]
    followups: list[FollowUpSuggestion]
    upcoming_commitments: list[dict[str, Any]]
    important_people: list[str]
    recent_decisions: list[dict[str, Any]]
    action_plans: list[dict[str, Any]]
    work_items: list[dict[str, Any]]
    top_priorities: list[RankedWorkItem]
    summary: OperationalSummary
    source_counts: dict[str, int]

    @classmethod
    def empty(cls, *, date: str | None = None, window_days: int = 14) -> "ContextSnapshot":
        generated_at = datetime.now(timezone.utc).isoformat()
        return cls(
            date=date or generated_at[:10],
            generated_at=generated_at,
            window_days=window_days,
            emails_pending=[],
            emails_critical=[],
            followups=[],
            upcoming_commitments=[],
            important_people=[],
            recent_decisions=[],
            action_plans=[],
            work_items=[],
            top_priorities=[],
            summary=OperationalSummary(
                total_emails=0,
                critical_emails=0,
                followups=0,
                pending_action_plans=0,
                top_category=None,
                top_priority=None,
                total_by_category={},
                total_by_priority={},
            ),
            source_counts={},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "date": self.date,
            "generated_at": self.generated_at,
            "window_days": self.window_days,
            "emails_pending": list(self.emails_pending),
            "emails_critical": list(self.emails_critical),
            "followups": [followup.to_dict() for followup in self.followups],
            "upcoming_commitments": list(self.upcoming_commitments),
            "important_people": list(self.important_people),
            "recent_decisions": list(self.recent_decisions),
            "action_plans": list(self.action_plans),
            "work_items": list(self.work_items),
            "top_priorities": [item.to_dict() for item in self.top_priorities],
            "summary": self.summary.to_dict(),
            "source_counts": dict(self.source_counts),
        }
