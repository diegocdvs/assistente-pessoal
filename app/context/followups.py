from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.context.models import FollowUpSuggestion
from app.context.ranking import _age_days, _parse_datetime


class FollowUpDetector:
    def __init__(self, *, stale_days: int = 7, sent_without_reply_days: int = 3) -> None:
        self.stale_days = stale_days
        self.sent_without_reply_days = sent_without_reply_days

    def detect(
        self,
        emails: list[dict[str, Any]],
        work_items: list[dict[str, Any]],
        classifications: dict[str, dict[str, Any]],
        action_plans: dict[str, list[dict[str, Any]]],
        *,
        now: datetime | None = None,
    ) -> list[FollowUpSuggestion]:
        now = now or datetime.now(timezone.utc)
        suggestions: list[FollowUpSuggestion] = []
        suggestions.extend(self._sent_without_reply(emails, now))
        suggestions.extend(self._old_pending_emails(emails, classifications, action_plans, now))
        suggestions.extend(self._forgotten_work_items(work_items, classifications, action_plans, now))
        return _dedupe(suggestions)

    def _sent_without_reply(self, emails: list[dict[str, Any]], now: datetime) -> list[FollowUpSuggestion]:
        by_thread: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for email in emails:
            thread_id = email.get("thread_id")
            if thread_id:
                by_thread[str(thread_id)].append(email)

        suggestions: list[FollowUpSuggestion] = []
        for thread_id, thread_emails in by_thread.items():
            ordered = sorted(thread_emails, key=lambda item: _parse_datetime(item.get("received_at")) or datetime.min.replace(tzinfo=timezone.utc))
            last = ordered[-1]
            if not _is_sent(last):
                continue
            age_days = _age_days(last.get("received_at"), now)
            if age_days is None or age_days < self.sent_without_reply_days:
                continue
            suggestions.append(
                FollowUpSuggestion(
                    id=f"followup:sent_without_reply:{last.get('account_id')}:{last.get('id')}",
                    type="sent_without_reply",
                    reason="Email enviado sem resposta recente detectada.",
                    account_id=str(last.get("account_id")),
                    email_id=str(last.get("id")),
                    thread_id=thread_id,
                    age_days=age_days,
                    payload={"subject": last.get("subject"), "sender": last.get("sender")},
                )
            )
        return suggestions

    def _old_pending_emails(
        self,
        emails: list[dict[str, Any]],
        classifications: dict[str, dict[str, Any]],
        action_plans: dict[str, list[dict[str, Any]]],
        now: datetime,
    ) -> list[FollowUpSuggestion]:
        suggestions: list[FollowUpSuggestion] = []
        for email in emails:
            if _is_sent(email):
                continue
            email_id = str(email.get("id"))
            classification = classifications.get(email_id, {})
            plans = action_plans.get(email_id, [])
            age_days = _age_days(email.get("received_at"), now)
            if age_days is None or age_days < self.stale_days:
                continue
            if classification.get("priority") in {"ruido", "baixa"}:
                continue
            if plans and all(plan.get("status") == "executed" for plan in plans):
                continue
            suggestions.append(
                FollowUpSuggestion(
                    id=f"followup:old_pending:{email.get('account_id')}:{email_id}",
                    type="old_pending",
                    reason="Item relevante antigo ainda aparece como pendente.",
                    account_id=str(email.get("account_id")),
                    email_id=email_id,
                    thread_id=email.get("thread_id"),
                    age_days=age_days,
                    payload={"category": classification.get("category"), "priority": classification.get("priority")},
                )
            )
        return suggestions

    def _forgotten_work_items(
        self,
        work_items: list[dict[str, Any]],
        classifications: dict[str, dict[str, Any]],
        action_plans: dict[str, list[dict[str, Any]]],
        now: datetime,
    ) -> list[FollowUpSuggestion]:
        suggestions: list[FollowUpSuggestion] = []
        for item in work_items:
            payload = item.get("payload") or {}
            message_id = str(payload.get("id") or payload.get("email_id") or item.get("id"))
            if message_id in classifications or action_plans.get(message_id):
                continue
            age_days = _age_days(payload.get("received_at") or item.get("created_at"), now)
            if age_days is None or age_days < self.stale_days:
                continue
            suggestions.append(
                FollowUpSuggestion(
                    id=f"followup:forgotten_work_item:{item.get('account_id')}:{message_id}",
                    type="forgotten_work_item",
                    reason="WorkItem antigo sem classificacao ou plano associado.",
                    account_id=str(item.get("account_id")),
                    work_item_id=str(item.get("id")),
                    email_id=message_id,
                    thread_id=payload.get("thread_id"),
                    age_days=age_days,
                    payload={"source": item.get("source"), "type": item.get("type")},
                )
            )
        return suggestions


def _is_sent(email: dict[str, Any]) -> bool:
    labels = {str(label).upper() for label in email.get("labels", [])}
    metadata = email.get("metadata") or {}
    direction = str(metadata.get("direction") or metadata.get("mail_direction") or "").lower()
    return "SENT" in labels or direction == "sent"


def _dedupe(suggestions: list[FollowUpSuggestion]) -> list[FollowUpSuggestion]:
    seen: set[str] = set()
    deduped: list[FollowUpSuggestion] = []
    for suggestion in suggestions:
        if suggestion.id in seen:
            continue
        seen.add(suggestion.id)
        deduped.append(suggestion)
    return deduped
