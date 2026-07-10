from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class CalendarSettings:
    enabled: bool = False
    provider: str = "google"
    lookahead_days: int = 7
    lookback_days: int = 1
    max_events: int = 100
    calendar_ids: tuple[str, ...] = ("primary",)
    include_declined: bool = False
    include_cancelled: bool = False
    workday_start: str = "08:00"
    workday_end: str = "18:00"
    min_free_window_minutes: int = 30
    timezone: str = "America/Sao_Paulo"

    def validate(self) -> None:
        if self.provider != "google":
            raise ValueError(f"CALENDAR_PROVIDER invalido: {self.provider}")
        if self.lookahead_days < 0 or self.lookahead_days > 31:
            raise ValueError("CALENDAR_LOOKAHEAD_DAYS deve estar entre 0 e 31.")
        if self.lookback_days < 0 or self.lookback_days > 31:
            raise ValueError("CALENDAR_LOOKBACK_DAYS deve estar entre 0 e 31.")
        if self.max_events < 1 or self.max_events > 2500:
            raise ValueError("CALENDAR_MAX_EVENTS deve estar entre 1 e 2500.")
        if not self.calendar_ids:
            raise ValueError("CALENDAR_IDS deve conter ao menos um calendario.")
        _parse_hhmm(self.workday_start)
        _parse_hhmm(self.workday_end)
        if self.min_free_window_minutes < 1:
            raise ValueError("CALENDAR_MIN_FREE_WINDOW_MINUTES deve ser maior que zero.")


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))
