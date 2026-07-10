from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

from app.calendar import (
    CalendarConflictDetector,
    CalendarDoubleCheck,
    CalendarEvent,
    CalendarSecurityAnalyzer,
    DailyAgendaBuilder,
    FreeTimeCalculator,
    GoogleCalendarConnector,
    InMemoryCalendarRepository,
    MeetingContextBuilder,
)
from app.calendar.repository import FirestoreCalendarRepository
from app.context import ContextEngine, InMemoryContextRepository
from scripts import calendar as calendar_cli


def event(event_id: str = "event-1", start: str = "2026-07-10T10:00:00+00:00", end: str = "2026-07-10T11:00:00+00:00", **kwargs) -> CalendarEvent:
    return CalendarEvent(
        id=event_id,
        provider="google_calendar",
        account_id="pessoal",
        calendar_id="primary",
        title=kwargs.get("title", "Reuniao Projeto"),
        description_summary=kwargs.get("description_summary"),
        location=kwargs.get("location"),
        start_at=start,
        end_at=end,
        timezone=kwargs.get("timezone", "America/Sao_Paulo"),
        all_day=kwargs.get("all_day", False),
        status=kwargs.get("status", "confirmed"),
        organizer=kwargs.get("organizer", "owner@example.com"),
        attendees=kwargs.get("attendees", ["person@example.com"]),
        attendee_count=1,
        user_response_status=kwargs.get("user_response_status", "accepted"),
        recurrence_id=kwargs.get("recurrence_id"),
        recurring=kwargs.get("recurring", False),
        meeting_url_present=kwargs.get("meeting_url_present", False),
        visibility="default",
        source_updated_at="2026-07-10T09:00:00Z",
    )


def test_calendar_event_to_work_item():
    work_item = event().to_work_item()

    assert work_item.type == "calendar_event"
    assert work_item.payload["provider"] == "google_calendar"


def test_google_calendar_connector_paginates_and_normalizes_events():
    service = fake_calendar_service(
        event_pages=[
            {"items": [google_payload("a")], "nextPageToken": "next"},
            {"items": [google_payload("b", all_day=True, recurring=True)]},
        ]
    )
    connector = GoogleCalendarConnector("project", service=service)
    account = fake_account()

    events = connector.fetch_events(
        account,
        calendar_ids=["primary"],
        time_min=datetime(2026, 7, 10, tzinfo=timezone.utc),
        time_max=datetime(2026, 7, 11, tzinfo=timezone.utc),
        max_results=10,
    )

    assert [item.id for item in events] == ["a", "b"]
    assert events[1].all_day is True
    assert events[1].recurring is True


def test_google_calendar_connector_filters_declined_and_cancelled():
    service = fake_calendar_service(
        event_pages=[
            {
                "items": [
                    google_payload("ok"),
                    google_payload("cancelled", status="cancelled"),
                    google_payload("declined", response="declined"),
                ]
            }
        ]
    )
    events = GoogleCalendarConnector("project", service=service).fetch_events(
        fake_account(),
        calendar_ids=["primary"],
        time_min=datetime(2026, 7, 10, tzinfo=timezone.utc),
        time_max=datetime(2026, 7, 11, tzinfo=timezone.utc),
        max_results=10,
    )

    assert [item.id for item in events] == ["ok"]


def test_repository_idempotency_and_firestore_mock():
    repo = InMemoryCalendarRepository()
    first = repo.upsert_event(event())
    second = repo.upsert_event(event())

    assert first.existed is False
    assert second.existed is True

    client = Mock()
    with patch("app.calendar.repository.firestore.Client", return_value=client):
        FirestoreCalendarRepository("project").upsert_event(event())
    client.collection.assert_called_with("accounts")


def test_context_snapshot_calendar_fields():
    repository = InMemoryContextRepository(calendar_events=[event().to_dict()])

    snapshot = ContextEngine(repository).build_snapshot(now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc))

    assert snapshot.calendar_events_upcoming == 1
    assert snapshot.meetings_count_today == 1
    assert snapshot.next_event["id"] == "event-1"


def test_free_time_and_conflict_detection():
    events = [
        event("a", "2026-07-10T09:00:00+00:00", "2026-07-10T10:00:00+00:00"),
        event("b", "2026-07-10T09:30:00+00:00", "2026-07-10T11:00:00+00:00"),
    ]

    windows = FreeTimeCalculator().calculate(events, day=date(2026, 7, 10), timezone="UTC", workday_start="08:00", workday_end="12:00")
    conflicts = CalendarConflictDetector().detect(events, timezone="America/Sao_Paulo")

    assert windows
    assert any(conflict.type == "overlap" for conflict in conflicts)


def test_meeting_context_relates_only_with_evidence():
    email = {"id": "email-1", "sender": "Person <person@example.com>", "subject": "Reuniao Projeto", "account_id": "pessoal"}
    unrelated = {"id": "email-2", "sender": "Other <other.test>", "subject": "Nada a ver", "account_id": "pessoal"}

    context = MeetingContextBuilder().build(event(), emails=[email, unrelated], work_items=[], action_plans=[], now=datetime(2026, 7, 10, 9, tzinfo=timezone.utc))

    assert [item["id"] for item in context.related_emails] == ["email-1"]
    assert "example.com" in context.participants


def test_daily_agenda_builder_is_deterministic():
    agenda = DailyAgendaBuilder().build(
        day=date(2026, 7, 10),
        timezone="UTC",
        events=[event()],
        critical_emails=[{"id": "email"}],
        followups=[],
        action_plans=[],
        subscriptions_waiting_approval=1,
        security_warnings=[],
        top_priorities=[],
        double_check_status="OK",
    )

    assert "Hoje: 1 compromissos." in agenda.summary_lines
    assert agenda.subscriptions_waiting_approval == 1


def test_calendar_security_assessment_does_not_access_urls():
    assessment = CalendarSecurityAnalyzer().analyze(
        event(description_summary="Veja https://bit.ly/x?url=https://evil.test", meeting_url_present=True),
        user_domain="example.com",
    )

    assert assessment.link_count == 1
    assert assessment.risk_score > 0


def test_calendar_double_check_reports_read_only_discrepancies():
    discrepancies = CalendarDoubleCheck().inspect(
        source_events=[{"id": "source"}],
        persisted_events=[{"id": "persisted", "provider": "bad"}],
        context_snapshot={"calendar_events_upcoming": 2},
        conflicts=[],
    )

    types = {item.type for item in discrepancies}
    assert "source_event_missing_in_persistence" in types
    assert "calendar_event_missing_schema_version" in types
    assert "calendar_event_provider_incorrect" in types


def test_calendar_cli_outputs_safe_json(monkeypatch, capsys):
    class FakeRepository:
        def __init__(self, *_args, **_kwargs):
            pass

        def load_context_data(self, *, account_ids=None, limit=100):
            from app.context.store import ContextData

            return ContextData(calendar_events=[event().to_dict()])

    monkeypatch.setattr(calendar_cli, "FirestoreContextRepository", FakeRepository)

    assert calendar_cli.main_with_args(["--json"]) == 0
    assert '"read_only": true' in capsys.readouterr().out


def fake_account():
    from app.core.accounts import MailAccount

    return MailAccount(id="pessoal", label="Pessoal", provider="gmail", email="user@example.com", enabled=True, secret_prefix="google")


def google_payload(event_id: str, *, all_day: bool = False, recurring: bool = False, status: str = "confirmed", response: str = "accepted"):
    start = {"date": "2026-07-10"} if all_day else {"dateTime": "2026-07-10T10:00:00+00:00", "timeZone": "America/Sao_Paulo"}
    end = {"date": "2026-07-11"} if all_day else {"dateTime": "2026-07-10T11:00:00+00:00", "timeZone": "America/Sao_Paulo"}
    payload = {
        "id": event_id,
        "summary": "Reuniao Projeto",
        "start": start,
        "end": end,
        "status": status,
        "organizer": {"email": "owner@example.com"},
        "attendees": [{"email": "user@example.com", "self": True, "responseStatus": response}],
        "updated": "2026-07-10T09:00:00Z",
    }
    if recurring:
        payload["recurringEventId"] = "series"
    return payload


def fake_calendar_service(*, event_pages):
    class Request:
        def __init__(self, pages):
            self.pages = pages
            self.calls = 0

        def execute(self):
            page = self.pages[min(self.calls, len(self.pages) - 1)]
            self.calls += 1
            return page

    request = Request(event_pages)

    class Events:
        def list(self, **_kwargs):
            return request

    class Service:
        def events(self):
            return Events()

    return Service()
