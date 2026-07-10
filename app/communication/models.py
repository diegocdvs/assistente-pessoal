from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from app.core.models import SCHEMA_VERSION


class SubscriptionStatus(str, Enum):
    DETECTED = "detected"
    ACTIVE = "active"
    FAVORITE = "favorite"
    IGNORED = "ignored"
    UNSUBSCRIBE_RECOMMENDED = "unsubscribe_recommended"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class SubscriptionApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True)
class UnsubscribeMethod:
    method: str
    target: str
    redacted_target: str
    one_click: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class SubscriptionDetectionResult:
    detected: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)
    parsed_methods: list[UnsubscribeMethod] = field(default_factory=list)
    list_id: str | None = None
    source_headers: dict[str, str] = field(default_factory=dict)
    risk_recommendation: str = "review_before_execution"

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "parsed_methods": [method.to_dict() for method in self.parsed_methods],
            "list_id": self.list_id,
            "source_headers": dict(self.source_headers),
            "risk_recommendation": self.risk_recommendation,
            "schema_version": SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class SubscriptionEntity:
    subscription_id: str
    account_id: str
    provider: str
    sender: str
    sender_domain: str | None
    display_name: str | None
    list_id: str | None
    category: str | None
    first_seen_at: str
    last_received_at: str
    message_count: int
    estimated_frequency: str
    unsubscribe_supported: bool
    unsubscribe_methods: list[dict[str, Any]]
    unsubscribe_url: str | None = None
    unsubscribe_email: str | None = None
    one_click_supported: bool = False
    status: str = SubscriptionStatus.DETECTED.value
    recommendation_score: int = 0
    recommendation_reasons: list[str] = field(default_factory=list)
    latest_security_risk_level: str | None = None
    latest_security_risk_score: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendationResult:
    recommendation_score: int
    recommendation_reasons: list[str]
    recommended: bool
    blocked_by_security: bool
    requires_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class SubscriptionApproval:
    subscription_id: str
    action_plan_id: str
    status: str = SubscriptionApprovalStatus.PENDING.value
    approval_id: str = field(default_factory=lambda: f"approval:{uuid4().hex}")
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: str | None = None
    decided_by: str | None = None
    decision_reason: str | None = None
    expires_at: str | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubscriptionCandidate:
    id: str
    account_id: str
    provider: str
    email_id: str
    sender: str
    sender_domain: str | None
    display_name: str | None
    unsubscribe_supported: bool
    unsubscribe_method: str | None
    unsubscribe_url: str | None = None
    unsubscribe_email: str | None = None
    list_id: str | None = None
    risk_level: str = "unknown"
    status: str = "detected"
    evidence: list[str] = field(default_factory=list)
    audit_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}
