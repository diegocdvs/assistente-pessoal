from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from typing import Any

from app.calendar.conflicts import CalendarConflictDetector
from app.calendar.free_time import FreeTimeCalculator
from app.calendar.models import CalendarEvent
from app.calendar.security import CalendarSecurityAnalyzer
from app.communication.models import SubscriptionCandidate
from app.communication.subscriptions import SubscriptionDetector
from app.context.followups import FollowUpDetector
from app.context.models import ContextSnapshot, OperationalSummary
from app.context.ranking import PriorityRanker
from app.context.store import ContextRepository
from app.security import RiskLevel, SecurityDecision, ThreatAnalyzer


class ContextEngine:
    def __init__(
        self,
        repository: ContextRepository,
        *,
        ranker: PriorityRanker | None = None,
        followup_detector: FollowUpDetector | None = None,
        subscription_detector: SubscriptionDetector | None = None,
        threat_analyzer: ThreatAnalyzer | None = None,
        free_time_calculator: FreeTimeCalculator | None = None,
        calendar_conflict_detector: CalendarConflictDetector | None = None,
        calendar_security_analyzer: CalendarSecurityAnalyzer | None = None,
        window_days: int = 14,
    ) -> None:
        self.repository = repository
        self.ranker = ranker or PriorityRanker()
        self.followup_detector = followup_detector or FollowUpDetector()
        self.subscription_detector = subscription_detector or SubscriptionDetector()
        self.threat_analyzer = threat_analyzer or ThreatAnalyzer()
        self.free_time_calculator = free_time_calculator or FreeTimeCalculator()
        self.calendar_conflict_detector = calendar_conflict_detector or CalendarConflictDetector()
        self.calendar_security_analyzer = calendar_security_analyzer or CalendarSecurityAnalyzer()
        self.window_days = window_days

    def build_snapshot(
        self,
        *,
        account_ids: list[str] | None = None,
        limit: int = 100,
        now: datetime | None = None,
    ) -> ContextSnapshot:
        now = now or datetime.now(timezone.utc)
        data = self.repository.load_context_data(account_ids=account_ids, limit=limit)
        emails = data.emails
        work_items = [_email_to_work_item(email) for email in emails]
        followups = self.followup_detector.detect(
            emails,
            work_items,
            data.classifications,
            data.action_plans,
            now=now,
        )
        subscription_candidates = self.subscription_detector.detect(emails)
        subscriptions = data.subscriptions
        security_assessments = [self.threat_analyzer.analyze(email) for email in emails]
        calendar_events = [_calendar_event_from_dict(event) for event in data.calendar_events]
        calendar_today = [event for event in calendar_events if _event_on_date(event, now.date())]
        calendar_tomorrow = [event for event in calendar_events if _event_on_date(event, (now + timedelta(days=1)).date())]
        calendar_conflicts = self.calendar_conflict_detector.detect(calendar_today, timezone="America/Sao_Paulo")
        calendar_security = [self.calendar_security_analyzer.analyze(event) for event in calendar_events]
        followup_ids = {
            value
            for followup in followups
            for value in (followup.email_id, followup.work_item_id)
            if value
        }
        top_priorities = self.ranker.rank(
            work_items,
            data.classifications,
            data.action_plans,
            followup_ids=followup_ids,
            limit=10,
            now=now,
        )
        action_plans = _all_action_plans(data.action_plans)
        summary = _build_summary(
            emails=emails,
            classifications=data.classifications,
            action_plans=action_plans,
            followup_count=len(followups),
            subscription_candidates=subscription_candidates,
            subscriptions=subscriptions,
        )

        return ContextSnapshot(
            date=now.date().isoformat(),
            generated_at=now.isoformat(),
            window_days=self.window_days,
            emails_pending=_pending_emails(emails, data.classifications),
            emails_critical=_critical_emails(emails, data.classifications),
            followups=followups,
            subscription_candidates=subscription_candidates,
            subscriptions_total=len(subscriptions) or len(subscription_candidates),
            subscriptions_active=_count_subscriptions(subscriptions, "active"),
            subscriptions_new=_count_subscriptions(subscriptions, "detected"),
            subscriptions_recommended_for_unsubscribe=_count_subscriptions(
                subscriptions,
                "unsubscribe_recommended",
                fallback=len([candidate for candidate in subscription_candidates if candidate.unsubscribe_supported]),
            ),
            subscriptions_waiting_approval=_count_subscriptions(subscriptions, "waiting_approval"),
            subscriptions_blocked_by_security=len(
                [item for item in subscriptions if item.get("latest_security_risk_level") in {"high", "critical"}]
            ),
            top_subscription_candidates=_top_subscription_candidates(subscriptions),
            calendar_events_today=[_safe_calendar_event(event) for event in calendar_today if event.status != "cancelled"],
            calendar_events_tomorrow=[_safe_calendar_event(event) for event in calendar_tomorrow if event.status != "cancelled"],
            calendar_events_upcoming=len(calendar_events),
            all_day_events_today=[_safe_calendar_event(event) for event in calendar_today if event.all_day],
            next_event=_safe_calendar_event(_next_event(calendar_events, now)) if _next_event(calendar_events, now) else None,
            meetings_count_today=len([event for event in calendar_today if not event.all_day and event.status != "cancelled"]),
            free_windows_today=[
                window.to_dict()
                for window in self.free_time_calculator.calculate(calendar_today, day=now.date(), timezone="America/Sao_Paulo")
            ],
            calendar_conflicts=[conflict.to_dict() for conflict in calendar_conflicts],
            declined_events=[_safe_calendar_event(event) for event in calendar_today if event.user_response_status == "declined"],
            calendar_security_warnings=[
                assessment.to_dict()
                for assessment in calendar_security
                if assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} or assessment.policy_decision == SecurityDecision.REVIEW
            ],
            upcoming_commitments=_upcoming_commitments(emails, data.classifications),
            important_people=_important_people(emails),
            recent_decisions=_recent_decisions(data.reports),
            action_plans=action_plans,
            work_items=work_items,
            top_priorities=top_priorities,
            high_risk_items=[
                assessment.to_dict()
                for assessment in security_assessments
                if assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
            ],
            warning_items=[
                assessment.to_dict()
                for assessment in security_assessments
                if assessment.policy_decision in {SecurityDecision.WARN, SecurityDecision.REVIEW}
            ],
            security_events=[
                event.to_dict()
                for assessment in security_assessments
                for event in assessment.events
            ],
            summary=summary,
            source_counts=dict(Counter(item.get("source", "unknown") for item in work_items)),
        )


def _email_to_work_item(email: dict[str, Any]) -> dict[str, Any]:
    provider = str(email.get("provider") or "unknown")
    message_id = str(email.get("id"))
    return {
        "id": f"{provider}:{message_id}",
        "source": provider,
        "type": "email",
        "account_id": email.get("account_id"),
        "created_at": _to_iso(email.get("received_at") or email.get("created_at") or email.get("last_seen_at")),
        "payload": dict(email),
    }


def _build_summary(
    *,
    emails: list[dict[str, Any]],
    classifications: dict[str, dict[str, Any]],
    action_plans: list[dict[str, Any]],
    followup_count: int,
    subscription_candidates: list[SubscriptionCandidate],
    subscriptions: list[dict[str, Any]] | None = None,
) -> OperationalSummary:
    by_category = Counter(
        classification.get("category")
        for classification in classifications.values()
        if classification.get("category")
    )
    by_priority = Counter(
        classification.get("priority")
        for classification in classifications.values()
        if classification.get("priority")
    )
    pending_plans = [
        plan
        for plan in action_plans
        if plan.get("status", "planned") in {"planned", "waiting_approval", "failed"}
    ]
    recommended = [candidate for candidate in subscription_candidates if candidate.unsubscribe_supported]
    subscriptions = subscriptions or []
    total_subscriptions = len(subscriptions) or len(subscription_candidates)
    recommended_count = _count_subscriptions(
        subscriptions,
        "unsubscribe_recommended",
        fallback=len(recommended),
    )
    blocked_count = len([item for item in subscriptions if item.get("latest_security_risk_level") in {"high", "critical"}])
    return OperationalSummary(
        total_emails=len(emails),
        critical_emails=by_priority.get("critica", 0),
        followups=followup_count,
        pending_action_plans=len(pending_plans),
        subscriptions_detected=len(subscription_candidates),
        subscriptions_recommended_for_unsubscribe=recommended_count,
        top_category=_most_common_key(by_category),
        top_priority=_most_common_key(by_priority),
        total_by_category=dict(by_category),
        total_by_priority=dict(by_priority),
        subscriptions_total=total_subscriptions,
        subscriptions_active=_count_subscriptions(subscriptions, "active"),
        subscriptions_new=_count_subscriptions(subscriptions, "detected"),
        subscriptions_waiting_approval=_count_subscriptions(subscriptions, "waiting_approval"),
        subscriptions_blocked_by_security=blocked_count,
        subscription_summary_lines=[
            f"Foram identificadas {total_subscriptions} inscricoes.",
            f"{recommended_count} sao candidatas a cancelamento.",
            f"{blocked_count} exige revisao de seguranca.",
        ],
    )


def _pending_emails(emails: list[dict[str, Any]], classifications: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        email
        for email in emails
        if classifications.get(str(email.get("id")), {}).get("priority") not in {"ruido", "baixa"}
    ]


def _critical_emails(emails: list[dict[str, Any]], classifications: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        email
        for email in emails
        if classifications.get(str(email.get("id")), {}).get("priority") == "critica"
    ]


def _upcoming_commitments(emails: list[dict[str, Any]], classifications: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "email_id": email.get("id"),
            "account_id": email.get("account_id"),
            "subject": email.get("subject"),
            "reason": classifications.get(str(email.get("id")), {}).get("reason"),
        }
        for email in emails
        if classifications.get(str(email.get("id")), {}).get("possible_event") is True
    ]


def _important_people(emails: list[dict[str, Any]], limit: int = 10) -> list[str]:
    senders = Counter(_sender_identity(email.get("sender", "")) for email in emails)
    senders.pop("", None)
    return [sender for sender, _count in senders.most_common(limit)]


def _recent_decisions(reports: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for report in reports:
        for action in report.get("planned_actions", []) if isinstance(report.get("planned_actions"), list) else []:
            decisions.append(
                {
                    "run_id": report.get("run_id"),
                    "type": action.get("type"),
                    "status": action.get("status"),
                    "reason": action.get("reason"),
                    "email_id": action.get("email_id"),
                    "account_id": action.get("account_id"),
                }
            )
    return decisions[:limit]


def _all_action_plans(action_plans: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [plan for plans in action_plans.values() for plan in plans]


def _most_common_key(counter: Counter) -> str | None:
    return counter.most_common(1)[0][0] if counter else None


def _count_subscriptions(subscriptions: list[dict[str, Any]], status: str, fallback: int = 0) -> int:
    if not subscriptions:
        return fallback
    return len([subscription for subscription in subscriptions if subscription.get("status") == status])


def _top_subscription_candidates(subscriptions: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    sanitized = []
    for subscription in sorted(subscriptions, key=lambda item: int(item.get("recommendation_score") or 0), reverse=True)[:limit]:
        payload = dict(subscription)
        payload.pop("unsubscribe_url", None)
        payload.pop("unsubscribe_email", None)
        sanitized.append(payload)
    return sanitized


def _sender_identity(value: str) -> str:
    name, address = parseaddr(value)
    return address or name or value


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _calendar_event_from_dict(payload: dict[str, Any]) -> CalendarEvent:
    return CalendarEvent(**payload)


def _event_on_date(event: CalendarEvent, day) -> bool:
    if event.all_day:
        return event.start_at == day.isoformat()
    return datetime.fromisoformat(event.start_at.replace("Z", "+00:00")).date() == day


def _next_event(events: list[CalendarEvent], now: datetime) -> CalendarEvent | None:
    future = [
        event
        for event in events
        if not event.all_day and event.status != "cancelled" and datetime.fromisoformat(event.start_at.replace("Z", "+00:00")) >= now
    ]
    return sorted(future, key=lambda event: event.start_at)[0] if future else None


def _safe_calendar_event(event: CalendarEvent) -> dict[str, Any]:
    payload = event.to_dict()
    payload["attendees"] = []
    payload["description_summary"] = payload["description_summary"][:120] if payload.get("description_summary") else None
    return payload
