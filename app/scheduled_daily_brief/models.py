from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.models import SCHEMA_VERSION


SCHEDULED_TRIGGERS = {"scheduler", "manual", "recovery", "test"}
SCHEDULED_STATUSES = {"pending", "running", "skipped", "draft_created", "delivered", "failed", "blocked"}
SCHEDULED_MODES = {"disabled", "draft", "send"}


@dataclass(frozen=True)
class ScheduledDailyBriefRun:
    run_id: str
    schedule_date: str
    timezone: str
    account_scope: str
    delivery_mode: str
    recipient_hash: str
    idempotency_key: str
    status: str
    started_at: str
    finished_at: str | None = None
    duration_seconds: float | None = None
    brief_id: str | None = None
    delivery_id: str | None = None
    attempt: int = 1
    trigger: str = "manual"
    error_code: str | None = None
    error_summary: str | None = None
    stage_counts: dict[str, int] = field(default_factory=dict)
    audit_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.delivery_mode not in SCHEDULED_MODES:
            raise ValueError(f"Modo agendado invalido: {self.delivery_mode}")
        if self.status not in SCHEDULED_STATUSES:
            raise ValueError(f"Status agendado invalido: {self.status}")
        if self.trigger not in SCHEDULED_TRIGGERS:
            raise ValueError(f"Trigger agendado invalido: {self.trigger}")
        if self.attempt < 1:
            raise ValueError("attempt deve ser >= 1.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_updates(self, **updates: Any) -> "ScheduledDailyBriefRun":
        payload = self.to_dict()
        payload.update(updates)
        return ScheduledDailyBriefRun(**payload)


@dataclass(frozen=True)
class ScheduledDailyBriefResult:
    run: ScheduledDailyBriefRun
    retryable: bool = False
    exit_code: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "retryable": self.retryable,
            "exit_code": self.exit_code,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
