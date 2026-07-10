from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.calendar.conflicts import CalendarConflictDetector
from app.calendar.free_time import FreeTimeCalculator
from app.calendar.models import CalendarEvent, DailyAgenda


class DailyAgendaBuilder:
    def __init__(
        self,
        *,
        free_time_calculator: FreeTimeCalculator | None = None,
        conflict_detector: CalendarConflictDetector | None = None,
    ) -> None:
        self.free_time_calculator = free_time_calculator or FreeTimeCalculator()
        self.conflict_detector = conflict_detector or CalendarConflictDetector()

    def build(
        self,
        *,
        day: date,
        timezone: str,
        events: list[CalendarEvent],
        critical_emails: list[dict],
        followups: list[dict],
        action_plans: list[dict],
        subscriptions_waiting_approval: int,
        security_warnings: list[dict],
        top_priorities: list[dict],
        double_check_status: str = "unknown",
    ) -> DailyAgenda:
        today_events = [event for event in events if _event_on_day(event, day, timezone) and event.status != "cancelled"]
        all_day = [event for event in today_events if event.all_day]
        timed = sorted([event for event in today_events if not event.all_day and event.user_response_status != "declined"], key=lambda event: event.start_at)
        free_windows = self.free_time_calculator.calculate(timed, day=day, timezone=timezone)
        conflicts = self.conflict_detector.detect(today_events, timezone=timezone)
        next_event = timed[0].to_dict() if timed else None
        lines = [
            f"Hoje: {len(today_events)} compromissos.",
            f"Proximo compromisso: {_safe_next(next_event)}.",
            f"{len(critical_emails)} emails criticos.",
            f"{len(conflicts)} conflitos de agenda.",
            f"{len(followups)} follow-ups.",
            f"{len(free_windows)} janelas livres.",
            f"auditoria: {double_check_status}.",
        ]
        return DailyAgenda(
            date=day.isoformat(),
            timezone=timezone,
            events_today=[_safe_event(event) for event in today_events],
            next_event=_safe_event_dict(next_event) if next_event else None,
            all_day_events=[_safe_event(event) for event in all_day],
            conflicts=[conflict.to_dict() for conflict in conflicts],
            free_windows=[window.to_dict() for window in free_windows],
            critical_emails=critical_emails,
            followups=followups,
            pending_action_plans=action_plans,
            subscriptions_waiting_approval=subscriptions_waiting_approval,
            security_warnings=security_warnings,
            double_check_status=double_check_status,
            top_priorities=top_priorities,
            summary_lines=lines,
        )


def _event_on_day(event: CalendarEvent, day: date, timezone: str) -> bool:
    if event.all_day:
        return event.start_at == day.isoformat()
    tz = ZoneInfo(timezone)
    return datetime.fromisoformat(event.start_at.replace("Z", "+00:00")).astimezone(tz).date() == day


def _safe_event(event: CalendarEvent) -> dict:
    payload = event.to_dict()
    payload["attendees"] = []
    payload["description_summary"] = payload["description_summary"][:120] if payload.get("description_summary") else None
    return payload


def _safe_event_dict(payload: dict) -> dict:
    payload = dict(payload)
    payload["attendees"] = []
    return payload


def _safe_next(payload: dict | None) -> str:
    if not payload:
        return "nenhum"
    return str(payload.get("start_at"))
