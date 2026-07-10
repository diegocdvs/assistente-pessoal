from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.communication.models import SubscriptionCandidate
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
    subscriptions_detected: int
    subscriptions_recommended_for_unsubscribe: int
    top_category: str | None
    top_priority: str | None
    total_by_category: dict[str, int]
    total_by_priority: dict[str, int]
    subscriptions_total: int = 0
    subscriptions_active: int = 0
    subscriptions_new: int = 0
    subscriptions_waiting_approval: int = 0
    subscriptions_blocked_by_security: int = 0
    subscription_summary_lines: list[str] = field(default_factory=list)

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
    subscription_candidates: list[SubscriptionCandidate]
    subscriptions_total: int
    subscriptions_active: int
    subscriptions_new: int
    subscriptions_recommended_for_unsubscribe: int
    subscriptions_waiting_approval: int
    subscriptions_blocked_by_security: int
    top_subscription_candidates: list[dict[str, Any]]
    calendar_events_today: list[dict[str, Any]]
    calendar_events_tomorrow: list[dict[str, Any]]
    calendar_events_upcoming: int
    all_day_events_today: list[dict[str, Any]]
    next_event: dict[str, Any] | None
    meetings_count_today: int
    free_windows_today: list[dict[str, Any]]
    calendar_conflicts: list[dict[str, Any]]
    declined_events: list[dict[str, Any]]
    calendar_security_warnings: list[dict[str, Any]]
    upcoming_commitments: list[dict[str, Any]]
    important_people: list[str]
    recent_decisions: list[dict[str, Any]]
    action_plans: list[dict[str, Any]]
    work_items: list[dict[str, Any]]
    top_priorities: list[RankedWorkItem]
    high_risk_items: list[dict[str, Any]]
    warning_items: list[dict[str, Any]]
    security_events: list[dict[str, Any]]
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
            subscription_candidates=[],
            subscriptions_total=0,
            subscriptions_active=0,
            subscriptions_new=0,
            subscriptions_recommended_for_unsubscribe=0,
            subscriptions_waiting_approval=0,
            subscriptions_blocked_by_security=0,
            top_subscription_candidates=[],
            calendar_events_today=[],
            calendar_events_tomorrow=[],
            calendar_events_upcoming=0,
            all_day_events_today=[],
            next_event=None,
            meetings_count_today=0,
            free_windows_today=[],
            calendar_conflicts=[],
            declined_events=[],
            calendar_security_warnings=[],
            upcoming_commitments=[],
            important_people=[],
            recent_decisions=[],
            action_plans=[],
            work_items=[],
            top_priorities=[],
            high_risk_items=[],
            warning_items=[],
            security_events=[],
            summary=OperationalSummary(
                total_emails=0,
                critical_emails=0,
                followups=0,
                pending_action_plans=0,
                subscriptions_detected=0,
                subscriptions_recommended_for_unsubscribe=0,
                subscriptions_total=0,
                subscriptions_active=0,
                subscriptions_new=0,
                subscriptions_waiting_approval=0,
                subscriptions_blocked_by_security=0,
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
            "subscription_candidates": [candidate.to_dict() for candidate in self.subscription_candidates],
            "subscriptions_total": self.subscriptions_total,
            "subscriptions_active": self.subscriptions_active,
            "subscriptions_new": self.subscriptions_new,
            "subscriptions_recommended_for_unsubscribe": self.subscriptions_recommended_for_unsubscribe,
            "subscriptions_waiting_approval": self.subscriptions_waiting_approval,
            "subscriptions_blocked_by_security": self.subscriptions_blocked_by_security,
            "top_subscription_candidates": list(self.top_subscription_candidates),
            "calendar_events_today": list(self.calendar_events_today),
            "calendar_events_tomorrow": list(self.calendar_events_tomorrow),
            "calendar_events_upcoming": self.calendar_events_upcoming,
            "all_day_events_today": list(self.all_day_events_today),
            "next_event": self.next_event,
            "meetings_count_today": self.meetings_count_today,
            "free_windows_today": list(self.free_windows_today),
            "calendar_conflicts": list(self.calendar_conflicts),
            "declined_events": list(self.declined_events),
            "calendar_security_warnings": list(self.calendar_security_warnings),
            "upcoming_commitments": list(self.upcoming_commitments),
            "important_people": list(self.important_people),
            "recent_decisions": list(self.recent_decisions),
            "action_plans": list(self.action_plans),
            "work_items": list(self.work_items),
            "top_priorities": [item.to_dict() for item in self.top_priorities],
            "high_risk_items": list(self.high_risk_items),
            "warning_items": list(self.warning_items),
            "security_events": list(self.security_events),
            "summary": self.summary.to_dict(),
            "source_counts": dict(self.source_counts),
        }
