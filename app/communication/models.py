from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.models import SCHEMA_VERSION


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
