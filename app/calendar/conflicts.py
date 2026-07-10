from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.calendar.models import CalendarConflict, CalendarEvent


class CalendarConflictDetector:
    def detect(self, events: list[CalendarEvent], *, timezone: str, workday_start: str = "08:00", workday_end: str = "18:00") -> list[CalendarConflict]:
        conflicts: list[CalendarConflict] = []
        timed = [event for event in events if not event.all_day and event.user_response_status != "declined"]
        ordered = sorted(timed, key=lambda event: event.start_at)
        for index, event in enumerate(ordered):
            if event.timezone and event.timezone != timezone:
                conflicts.append(CalendarConflict("timezone_inconsistent", "warning", [event.id], "Timezone do evento difere da configuracao."))
            if event.metadata.get("security_risk_level") in {"high", "critical"}:
                conflicts.append(CalendarConflict("high_risk_event", "error", [event.id], "Evento exige revisao de seguranca."))
            for other in ordered[index + 1 :]:
                if _start(other) < _end(event) and _end(other) > _start(event):
                    conflicts.append(CalendarConflict("overlap", "error", [event.id, other.id], "Eventos sobrepostos."))
                if event.title == other.title and event.start_at == other.start_at:
                    conflicts.append(CalendarConflict("apparent_duplicate", "warning", [event.id, other.id], "Eventos aparentam duplicidade."))
        return conflicts


def _start(event: CalendarEvent) -> datetime:
    return datetime.fromisoformat(event.start_at.replace("Z", "+00:00"))


def _end(event: CalendarEvent) -> datetime:
    return datetime.fromisoformat(event.end_at.replace("Z", "+00:00"))
