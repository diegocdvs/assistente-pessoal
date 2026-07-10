from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

from app.calendar.models import CalendarEvent, MeetingContext


class MeetingContextBuilder:
    def build(
        self,
        event: CalendarEvent,
        *,
        emails: list[dict[str, Any]],
        work_items: list[dict[str, Any]],
        action_plans: list[dict[str, Any]],
        security_warnings: list[dict[str, Any]] | None = None,
        now: datetime | None = None,
    ) -> MeetingContext:
        now = now or datetime.now(timezone.utc)
        participants = sorted(set(event.attendees + ([event.organizer] if event.organizer else [])))
        related_emails = [email for email in emails if _email_related(email, event, participants)]
        related_work_items = [
            item for item in work_items if any(email.get("id") == (item.get("payload") or {}).get("id") for email in related_emails)
        ]
        related_action_plans = [
            plan for plan in action_plans if plan.get("payload", {}).get("email_id") in {email.get("id") for email in related_emails}
        ]
        minutes_until = int((_parse_dt(event.start_at) - now).total_seconds() // 60) if event.start_at else None
        notes = []
        if related_emails:
            notes.append("Ha emails relacionados por participante ou titulo.")
        if security_warnings:
            notes.append("Ha alertas de seguranca associados ao compromisso.")
        return MeetingContext(
            calendar_event_id=event.id,
            title=event.title,
            starts_at=event.start_at,
            minutes_until_start=minutes_until,
            participants=_redact_participants(participants),
            related_emails=[_safe_email(email) for email in related_emails],
            related_work_items=related_work_items,
            related_action_plans=related_action_plans,
            security_warnings=security_warnings or [],
            preparation_notes=notes,
        )


def _email_related(email: dict[str, Any], event: CalendarEvent, participants: list[str]) -> bool:
    sender = parseaddr(str(email.get("sender") or ""))[1].lower()
    participant_domains = {participant.split("@", 1)[1].lower() for participant in participants if "@" in participant}
    if sender and sender in {participant.lower() for participant in participants}:
        return True
    if "@" in sender and sender.split("@", 1)[1].lower() in participant_domains:
        return True
    title_terms = {term.lower() for term in event.title.split() if len(term) >= 4}
    subject_terms = {term.lower() for term in str(email.get("subject") or "").split() if len(term) >= 4}
    return bool(title_terms & subject_terms and len(title_terms & subject_terms) >= 2)


def _safe_email(email: dict[str, Any]) -> dict[str, Any]:
    return {"id": email.get("id"), "account_id": email.get("account_id"), "subject": email.get("subject")}


def _redact_participants(participants: list[str]) -> list[str]:
    return [participant if "@" not in participant else participant.split("@", 1)[1] for participant in participants]


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
