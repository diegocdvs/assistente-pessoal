from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.daily_brief.models import DailyBrief
from app.daily_brief_delivery.models import DailyBriefDeliveryRecord, DeliveryPolicyResult


@dataclass(frozen=True)
class DeliveryPolicySettings:
    enabled: bool = False
    mode: str = "disabled"
    recipients: tuple[str, ...] = ()
    allow_send: bool = False
    start_hour: int = 5
    end_hour: int = 11
    timezone: str = "America/Sao_Paulo"


class DailyBriefDeliveryPolicy:
    def evaluate(
        self,
        brief: DailyBrief,
        *,
        settings: DeliveryPolicySettings,
        recipient: str | None,
        mode: str | None = None,
        existing_record: DailyBriefDeliveryRecord | None = None,
        force: bool = False,
        now: datetime | None = None,
    ) -> DeliveryPolicyResult:
        effective_mode = mode or settings.mode
        if effective_mode == "disabled" or not settings.enabled:
            return DeliveryPolicyResult("BLOCK", "delivery disabled", "disabled")
        if effective_mode not in {"draft", "send"}:
            return DeliveryPolicyResult("BLOCK", f"unsupported delivery mode: {effective_mode}", "disabled")
        if not recipient:
            return DeliveryPolicyResult("BLOCK", "recipient not configured", effective_mode)
        normalized_recipient = recipient.strip().lower()
        allowlist = tuple(item.strip().lower() for item in settings.recipients if item.strip())
        if "*" in allowlist or normalized_recipient not in allowlist:
            return DeliveryPolicyResult("BLOCK", "recipient outside allowlist", effective_mode)
        if existing_record and not force:
            return DeliveryPolicyResult("BLOCK", "idempotency key already delivered", effective_mode)
        if not _inside_window(settings, now):
            return DeliveryPolicyResult("REVIEW", "outside configured delivery window", effective_mode)
        if brief.status == "ERROR":
            return DeliveryPolicyResult("BLOCK", "brief status ERROR blocks delivery", effective_mode)
        if brief.open_discrepancies:
            return DeliveryPolicyResult("REVIEW", "brief has open discrepancies", effective_mode)
        if brief.high_risk_items and effective_mode == "send":
            return DeliveryPolicyResult("REVIEW", "high risk items require review before send", effective_mode)
        if effective_mode == "draft":
            return DeliveryPolicyResult("ALLOW_DRAFT", "draft allowed by policy", effective_mode)
        if effective_mode == "send" and settings.allow_send:
            return DeliveryPolicyResult("ALLOW_SEND", "send explicitly allowed by policy", effective_mode)
        return DeliveryPolicyResult("BLOCK", "send mode requires explicit allow_send", effective_mode)


def _inside_window(settings: DeliveryPolicySettings, now: datetime | None) -> bool:
    zone = ZoneInfo(settings.timezone)
    current = now.astimezone(zone) if now else datetime.now(zone)
    if settings.start_hour <= settings.end_hour:
        return settings.start_hour <= current.hour < settings.end_hour
    return current.hour >= settings.start_hour or current.hour < settings.end_hour
