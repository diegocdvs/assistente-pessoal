from __future__ import annotations

from app.security.models import (
    AttachmentAssessment,
    HeaderAssessment,
    LinkAssessment,
    RiskLevel,
    SecurityAssessment,
    SecurityEvent,
    SecurityEventType,
)


class SecurityEventFactory:
    def build(
        self,
        *,
        provider: str,
        source_id: str,
        risk_level: RiskLevel,
        links: list[LinkAssessment],
        attachments: list[AttachmentAssessment],
        headers: HeaderAssessment,
    ) -> list[SecurityEvent]:
        events: list[SecurityEvent] = []
        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            events.append(SecurityEvent(SecurityEventType.HIGH_RISK_DETECTED, source_id, provider, "High risk assessment.", risk_level))
        if any(attachment.suspicious for attachment in attachments):
            events.append(SecurityEvent(SecurityEventType.SUSPICIOUS_ATTACHMENT, source_id, provider, "Suspicious attachment detected.", risk_level))
        if headers.spoofing_signals:
            events.append(SecurityEvent(SecurityEventType.SPOOFING_DETECTED, source_id, provider, "Spoofing signals detected.", risk_level))
        if headers.list_unsubscribe or headers.list_id:
            events.append(SecurityEvent(SecurityEventType.SUBSCRIPTION_DETECTED, source_id, provider, "Subscription headers detected.", RiskLevel.LOW))
        if any(link.suspicious for link in links):
            events.append(SecurityEvent(SecurityEventType.LINK_WARNING, source_id, provider, "Suspicious link signal detected.", risk_level))
        return events


def assessment_events(assessment: SecurityAssessment) -> list[dict]:
    return [event.to_dict() for event in assessment.events]
