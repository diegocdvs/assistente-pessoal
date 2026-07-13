"""Safe Daily Brief email delivery capability."""

from app.daily_brief_delivery.double_check import DailyBriefDeliveryDoubleCheck, DailyBriefDeliveryFinding
from app.daily_brief_delivery.gmail import (
    GMAIL_DRAFT_SCOPE,
    GMAIL_SEND_SCOPE,
    GmailDailyBriefDeliveryClient,
    NoopDailyBriefDeliveryClient,
)
from app.daily_brief_delivery.models import DailyBriefDeliveryRecord, DailyBriefEmailMessage, DeliveryPolicyResult
from app.daily_brief_delivery.policy import DailyBriefDeliveryPolicy, DeliveryPolicySettings
from app.daily_brief_delivery.renderers import DailyBriefEmailRenderer, DailyBriefSubjectBuilder
from app.daily_brief_delivery.repository import FirestoreDailyBriefDeliveryRepository, InMemoryDailyBriefDeliveryRepository
from app.daily_brief_delivery.service import DailyBriefDeliveryService

__all__ = [
    "DailyBriefDeliveryDoubleCheck",
    "DailyBriefDeliveryFinding",
    "DailyBriefDeliveryPolicy",
    "DailyBriefDeliveryRecord",
    "DailyBriefDeliveryService",
    "DailyBriefEmailMessage",
    "DailyBriefEmailRenderer",
    "DailyBriefSubjectBuilder",
    "DeliveryPolicyResult",
    "DeliveryPolicySettings",
    "FirestoreDailyBriefDeliveryRepository",
    "GMAIL_DRAFT_SCOPE",
    "GMAIL_SEND_SCOPE",
    "GmailDailyBriefDeliveryClient",
    "InMemoryDailyBriefDeliveryRepository",
    "NoopDailyBriefDeliveryClient",
]
