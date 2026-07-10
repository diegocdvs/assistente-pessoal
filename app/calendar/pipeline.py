from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.calendar.agenda import DailyAgendaBuilder
from app.calendar.config import CalendarSettings
from app.calendar.google import GoogleCalendarConnector
from app.calendar.repository import CalendarRepository, FirestoreCalendarRepository
from app.core.accounts import AccountManager, MailAccount

logger = logging.getLogger(__name__)


class CalendarReadOnlyPipeline:
    def __init__(
        self,
        *,
        settings: CalendarSettings,
        account_manager: AccountManager,
        connector: GoogleCalendarConnector,
        repository: CalendarRepository,
        agenda_builder: DailyAgendaBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.account_manager = account_manager
        self.connector = connector
        self.repository = repository
        self.agenda_builder = agenda_builder or DailyAgendaBuilder()

    @classmethod
    def default(cls, *, project_id: str, account_manager: AccountManager, settings: CalendarSettings) -> "CalendarReadOnlyPipeline":
        return cls(
            settings=settings,
            account_manager=account_manager,
            connector=GoogleCalendarConnector(project_id),
            repository=FirestoreCalendarRepository(project_id),
        )

    def fetch_and_persist(self, *, now: datetime | None = None) -> dict[str, Any]:
        self.settings.validate()
        if not self.settings.enabled:
            return {"enabled": False, "events_fetched": 0, "events_persisted": 0, "errors": []}
        now = now or datetime.now(timezone.utc)
        time_min = now - timedelta(days=self.settings.lookback_days)
        time_max = now + timedelta(days=self.settings.lookahead_days)
        events_fetched = 0
        events_persisted = 0
        errors: list[dict[str, str]] = []
        for account in self._calendar_accounts():
            try:
                events = self.connector.fetch_events(
                    account,
                    calendar_ids=list(self.settings.calendar_ids),
                    time_min=time_min,
                    time_max=time_max,
                    max_results=self.settings.max_events,
                    include_cancelled=self.settings.include_cancelled,
                    include_declined=self.settings.include_declined,
                )
                events_fetched += len(events)
                for event in events:
                    self.repository.upsert_event(event)
                    events_persisted += 1
                logger.info(
                    "calendar_pipeline",
                    extra={
                        "account_id": account.id,
                        "provider": "google_calendar",
                        "stage": "calendar_persist",
                        "events_fetched": len(events),
                        "events_persisted": len(events),
                        "status": "ok",
                    },
                )
            except Exception as exc:
                errors.append({"account_id": account.id, "provider": "google_calendar", "error": str(exc)})
        return {"enabled": True, "events_fetched": events_fetched, "events_persisted": events_persisted, "errors": errors}

    def _calendar_accounts(self) -> list[MailAccount]:
        return [account for account in self.account_manager.enabled_accounts() if account.calendar_enabled]
