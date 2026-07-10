from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from app.core.models import SCHEMA_VERSION


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    REVIEW = "review"
    BLOCK = "block"
    QUARANTINE = "quarantine"


class SecurityEventType(str, Enum):
    HIGH_RISK_DETECTED = "HighRiskDetected"
    SUSPICIOUS_ATTACHMENT = "SuspiciousAttachment"
    SPOOFING_DETECTED = "SpoofingDetected"
    SUBSCRIPTION_DETECTED = "SubscriptionDetected"
    LINK_WARNING = "LinkWarning"


@dataclass(frozen=True)
class DomainAssessment:
    value: str
    normalized: str
    is_empty: bool = False
    is_ip_literal: bool = False
    has_unicode: bool = False
    has_punycode: bool = False
    uncommon_tld: bool = False
    looks_like: str | None = None
    risk_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class LinkAssessment:
    url: str
    protocol: str | None
    domain: str | None
    suspicious: bool
    risk_reasons: list[str]
    is_ip_literal: bool = False
    is_shortener: bool = False
    has_unicode: bool = False
    has_punycode: bool = False
    uncommon_port: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class AttachmentAssessment:
    filename: str
    extension: str | None
    mime_type: str | None
    size_bytes: int | None
    suspicious: bool
    risk_reasons: list[str]
    has_double_extension: bool = False
    is_executable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class HeaderAssessment:
    list_unsubscribe: bool
    list_id: bool
    auto_submitted: str | None
    precedence: str | None
    reply_to_differs: bool
    return_path: str | None
    authentication_signals: list[str]
    spoofing_signals: list[str]
    suspicious_headers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class SecurityEvent:
    type: SecurityEventType
    source_id: str
    provider: str
    reason: str
    severity: RiskLevel
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"security-event:{uuid4().hex}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["type"] = self.type.value
        payload["severity"] = self.severity.value
        return {**payload, "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class SecurityAssessment:
    assessment_id: str
    provider: str
    source_id: str
    risk_score: int
    risk_level: RiskLevel
    risk_reasons: list[str]
    link_count: int
    attachment_count: int
    external_images: int
    suspicious_headers: list[str]
    spoofing_signals: list[str]
    authentication_signals: list[str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = SCHEMA_VERSION
    policy_decision: SecurityDecision = SecurityDecision.ALLOW
    links: list[LinkAssessment] = field(default_factory=list)
    attachments: list[AttachmentAssessment] = field(default_factory=list)
    events: list[SecurityEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["risk_level"] = self.risk_level.value
        payload["policy_decision"] = self.policy_decision.value
        payload["links"] = [link.to_dict() for link in self.links]
        payload["attachments"] = [attachment.to_dict() for attachment in self.attachments]
        payload["events"] = [event.to_dict() for event in self.events]
        return payload


@dataclass(frozen=True)
class SecurityAuditRecord:
    assessment_id: str
    source_id: str
    provider: str
    decision: SecurityDecision
    risk_score: int
    risk_level: RiskLevel
    reason_count: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_id: str = field(default_factory=lambda: f"security-audit:{uuid4().hex}")
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        payload["risk_level"] = self.risk_level.value
        return {**payload, "schema_version": SCHEMA_VERSION}
