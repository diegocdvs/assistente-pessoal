from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.models import SCHEMA_VERSION


DELIVERY_MODES = {"disabled", "draft", "send"}
DELIVERY_STATUSES = {"skipped", "blocked", "draft_created", "sent", "failed"}
POLICY_DECISIONS = {"ALLOW_DRAFT", "ALLOW_SEND", "BLOCK", "REVIEW"}


@dataclass(frozen=True)
class DailyBriefEmailMessage:
    message_id: str
    brief_id: str
    account_id: str
    recipient: str
    subject: str
    text_body: str
    html_body: str
    delivery_mode: str
    idempotency_key: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.delivery_mode not in DELIVERY_MODES:
            raise ValueError(f"Modo de delivery invalido: {self.delivery_mode}")
        if not self.recipient or "@" not in self.recipient:
            raise ValueError("Destinatario de Daily Brief invalido.")

    def to_dict(self, *, include_body: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        if not include_body:
            payload.pop("text_body", None)
            payload.pop("html_body", None)
        return payload


@dataclass(frozen=True)
class DeliveryPolicyResult:
    decision: str
    reason: str
    effective_mode: str

    def __post_init__(self) -> None:
        if self.decision not in POLICY_DECISIONS:
            raise ValueError(f"Decisao de policy invalida: {self.decision}")
        if self.effective_mode not in DELIVERY_MODES:
            raise ValueError(f"Modo efetivo invalido: {self.effective_mode}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyBriefDeliveryRecord:
    delivery_id: str
    brief_id: str
    account_id: str
    recipient: str
    mode: str
    policy_decision: str
    policy_reason: str
    status: str
    idempotency_key: str
    gmail_draft_id: str | None = None
    gmail_message_id: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.mode not in DELIVERY_MODES:
            raise ValueError(f"Modo de delivery invalido: {self.mode}")
        if self.policy_decision not in POLICY_DECISIONS:
            raise ValueError(f"Decisao de policy invalida: {self.policy_decision}")
        if self.status not in DELIVERY_STATUSES:
            raise ValueError(f"Status de delivery invalido: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
