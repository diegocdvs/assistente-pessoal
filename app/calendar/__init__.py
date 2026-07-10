"""Read-only calendar capability."""

from app.calendar.agenda import DailyAgendaBuilder
from app.calendar.base import CalendarConnector
from app.calendar.config import CalendarSettings
from app.calendar.conflicts import CalendarConflictDetector
from app.calendar.double_check import CalendarDoubleCheck
from app.calendar.free_time import FreeTimeCalculator
from app.calendar.google import GOOGLE_CALENDAR_READONLY_SCOPES, GoogleCalendarConnector
from app.calendar.meeting_context import MeetingContextBuilder
from app.calendar.models import CalendarConflict, CalendarEvent, DailyAgenda, FreeWindow, MeetingContext
from app.calendar.repository import FirestoreCalendarRepository, InMemoryCalendarRepository
from app.calendar.security import CalendarSecurityAnalyzer

__all__ = [
    "CalendarConflict",
    "CalendarConflictDetector",
    "CalendarConnector",
    "CalendarDoubleCheck",
    "CalendarEvent",
    "CalendarSecurityAnalyzer",
    "CalendarSettings",
    "DailyAgenda",
    "DailyAgendaBuilder",
    "FirestoreCalendarRepository",
    "FreeTimeCalculator",
    "FreeWindow",
    "GOOGLE_CALENDAR_READONLY_SCOPES",
    "GoogleCalendarConnector",
    "InMemoryCalendarRepository",
    "MeetingContext",
    "MeetingContextBuilder",
]
