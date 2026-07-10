from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.calendar.models import CalendarEvent, FreeWindow


class FreeTimeCalculator:
    def calculate(
        self,
        events: list[CalendarEvent],
        *,
        day: date,
        timezone: str,
        workday_start: str = "08:00",
        workday_end: str = "18:00",
        min_minutes: int = 30,
    ) -> list[FreeWindow]:
        tz = ZoneInfo(timezone)
        start = datetime.combine(day, _parse_time(workday_start), tzinfo=tz)
        end = datetime.combine(day, _parse_time(workday_end), tzinfo=tz)
        busy = sorted(
            (_parse_dt(event.start_at, tz), _parse_dt(event.end_at, tz))
            for event in events
            if not event.all_day and event.user_response_status != "declined"
        )
        cursor = start
        windows: list[FreeWindow] = []
        for event_start, event_end in busy:
            if event_end <= start or event_start >= end:
                continue
            event_start = max(event_start, start)
            event_end = min(event_end, end)
            if event_start > cursor and (event_start - cursor).total_seconds() >= min_minutes * 60:
                windows.append(_window(cursor, event_start))
            cursor = max(cursor, event_end)
        if end > cursor and (end - cursor).total_seconds() >= min_minutes * 60:
            windows.append(_window(cursor, end))
        return windows


def _window(start: datetime, end: datetime) -> FreeWindow:
    return FreeWindow(start_at=start.isoformat(), end_at=end.isoformat(), duration_minutes=int((end - start).total_seconds() // 60))


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _parse_dt(value: str, tz: ZoneInfo) -> datetime:
    if len(value) == 10:
        return datetime.fromisoformat(value).replace(tzinfo=tz)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)
