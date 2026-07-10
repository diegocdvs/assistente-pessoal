from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.calendar.models import CalendarEvent, CalendarListEntry
from app.core.accounts import MailAccount


class CalendarConnector(Protocol):
    provider: str

    def list_calendars(self, account: MailAccount) -> list[CalendarListEntry]:
        pass

    def fetch_events(
        self,
        account: MailAccount,
        *,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime,
        max_results: int,
        include_cancelled: bool = False,
        include_declined: bool = False,
    ) -> list[CalendarEvent]:
        pass
