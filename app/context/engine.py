from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

from app.communication.models import SubscriptionCandidate
from app.communication.subscriptions import SubscriptionDetector
from app.context.followups import FollowUpDetector
from app.context.models import ContextSnapshot, OperationalSummary
from app.context.ranking import PriorityRanker
from app.context.store import ContextRepository


class ContextEngine:
    def __init__(
        self,
        repository: ContextRepository,
        *,
        ranker: PriorityRanker | None = None,
        followup_detector: FollowUpDetector | None = None,
        subscription_detector: SubscriptionDetector | None = None,
        window_days: int = 14,
    ) -> None:
        self.repository = repository
        self.ranker = ranker or PriorityRanker()
        self.followup_detector = followup_detector or FollowUpDetector()
        self.subscription_detector = subscription_detector or SubscriptionDetector()
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
        )

        return ContextSnapshot(
            date=now.date().isoformat(),
            generated_at=now.isoformat(),
            window_days=self.window_days,
            emails_pending=_pending_emails(emails, data.classifications),
            emails_critical=_critical_emails(emails, data.classifications),
            followups=followups,
            subscription_candidates=subscription_candidates,
            upcoming_commitments=_upcoming_commitments(emails, data.classifications),
            important_people=_important_people(emails),
            recent_decisions=_recent_decisions(data.reports),
            action_plans=action_plans,
            work_items=work_items,
            top_priorities=top_priorities,
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
    return OperationalSummary(
        total_emails=len(emails),
        critical_emails=by_priority.get("critica", 0),
        followups=followup_count,
        pending_action_plans=len(pending_plans),
        subscriptions_detected=len(subscription_candidates),
        subscriptions_recommended_for_unsubscribe=len(recommended),
        top_category=_most_common_key(by_category),
        top_priority=_most_common_key(by_priority),
        total_by_category=dict(by_category),
        total_by_priority=dict(by_priority),
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


def _sender_identity(value: str) -> str:
    name, address = parseaddr(value)
    return address or name or value


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
