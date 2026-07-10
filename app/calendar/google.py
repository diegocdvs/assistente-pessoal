from __future__ import annotations

import json
import logging
from datetime import datetime
from html import unescape
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.calendar.models import CalendarEvent, CalendarListEntry
from app.connectors.secrets import SecretReader
from app.core.accounts import MailAccount

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_READONLY_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
]


class CalendarPermissionError(RuntimeError):
    pass


class GoogleCalendarConnector:
    provider = "google_calendar"

    def __init__(self, project_id: str, secret_reader: SecretReader | None = None, service: Any | None = None) -> None:
        self.project_id = project_id
        self.secret_reader = secret_reader
        self._service = service

    def list_calendars(self, account: MailAccount) -> list[CalendarListEntry]:
        service = self._service or self._build_service(account)
        entries: list[CalendarListEntry] = []
        page_token = None
        try:
            while True:
                response = service.calendarList().list(pageToken=page_token).execute()
                for item in response.get("items", []):
                    entries.append(
                        CalendarListEntry(
                            id=item["id"],
                            provider=self.provider,
                            account_id=account.id,
                            summary=item.get("summary", ""),
                            timezone=item.get("timeZone"),
                            primary=bool(item.get("primary", False)),
                            access_role=item.get("accessRole"),
                        )
                    )
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as exc:
            raise _calendar_permission_error(exc) from exc
        return entries

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
        service = self._service or self._build_service(account)
        events: list[CalendarEvent] = []
        for calendar_id in calendar_ids:
            page_token = None
            try:
                while True:
                    response = service.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min.isoformat(),
                        timeMax=time_max.isoformat(),
                        maxResults=min(max_results, 2500),
                        singleEvents=True,
                        orderBy="startTime",
                        showDeleted=include_cancelled,
                        pageToken=page_token,
                    ).execute()
                    for item in response.get("items", []):
                        event = self._to_calendar_event(account, calendar_id, item)
                        if not include_cancelled and event.status == "cancelled":
                            continue
                        if not include_declined and event.user_response_status == "declined":
                            continue
                        events.append(event)
                        if len(events) >= max_results:
                            return events
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
            except HttpError as exc:
                raise _calendar_permission_error(exc) from exc
        logger.info(
            "calendar_fetch_completed",
            extra={
                "account_id": account.id,
                "provider": self.provider,
                "stage": "calendar_fetch",
                "events_fetched": len(events),
                "status": "ok",
            },
        )
        return events

    def _build_service(self, account: MailAccount) -> Any:
        secret_reader = self.secret_reader or SecretReader(self.project_id)
        client_config = json.loads(secret_reader.read_text(f"{account.secret_prefix}-client-secret-json"))
        refresh_token = secret_reader.read_text(f"{account.secret_prefix}-refresh-token").strip()
        installed = client_config.get("installed") or client_config.get("web") or {}
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=installed.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=installed["client_id"],
            client_secret=installed["client_secret"],
            scopes=GOOGLE_CALENDAR_READONLY_SCOPES,
        )
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    def _to_calendar_event(self, account: MailAccount, calendar_id: str, item: dict[str, Any]) -> CalendarEvent:
        start = item.get("start", {})
        end = item.get("end", {})
        all_day = "date" in start
        attendees = item.get("attendees") or []
        user_attendee = next((attendee for attendee in attendees if attendee.get("self")), {})
        description = _summarize_description(item.get("description"))
        meeting_url_present = bool(item.get("hangoutLink") or item.get("conferenceData"))
        return CalendarEvent(
            id=item["id"],
            provider=self.provider,
            account_id=account.id,
            calendar_id=calendar_id,
            title=item.get("summary") or "(sem titulo)",
            description_summary=description,
            location=item.get("location"),
            start_at=start.get("dateTime") or start.get("date"),
            end_at=end.get("dateTime") or end.get("date"),
            timezone=start.get("timeZone") or end.get("timeZone"),
            all_day=all_day,
            status=item.get("status", "confirmed"),
            organizer=(item.get("organizer") or {}).get("email"),
            attendees=[attendee.get("email") for attendee in attendees if attendee.get("email")],
            attendee_count=len(attendees),
            user_response_status=user_attendee.get("responseStatus"),
            recurrence_id=item.get("recurringEventId"),
            recurring=bool(item.get("recurringEventId") or item.get("recurrence")),
            meeting_url_present=meeting_url_present,
            visibility=item.get("visibility"),
            source_updated_at=item.get("updated"),
            metadata={
                "google_event_type": item.get("eventType"),
                "google_sequence": item.get("sequence"),
                "google_creator_self": (item.get("creator") or {}).get("self"),
                "google_calendar_id": calendar_id,
            },
        )


def _calendar_permission_error(exc: HttpError) -> CalendarPermissionError:
    text = str(exc)
    if "insufficientPermissions" in text or "insufficient authentication scopes" in text or "invalid_scope" in text:
        return CalendarPermissionError(
            "Google Calendar sem escopo read-only suficiente. Reautorize o OAuth com "
            "calendar.events.readonly e calendar.calendarlist.readonly e atualize o refresh token no Secret Manager."
        )
    return CalendarPermissionError(f"Falha ao ler Google Calendar: {exc}")


def _summarize_description(value: str | None, limit: int = 180) -> str | None:
    if not value:
        return None
    text = " ".join(unescape(value).split())
    return text[:limit]
