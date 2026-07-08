from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = "0.2"


class Category(str, Enum):
    FINANCEIRO = "financeiro"
    COMPRA = "compra"
    ENTREGA = "entrega"
    EVENTO = "evento"
    TRABALHO = "trabalho"
    SEGURANCA = "seguranca"
    PROMOCAO = "promocao"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    EDUCACAO = "educacao"
    VIAGEM = "viagem"
    SAUDE = "saude"
    SISTEMA = "sistema"
    OUTROS = "outros"


class Priority(str, Enum):
    CRITICA = "critica"
    ALTA = "alta"
    NORMAL = "normal"
    BAIXA = "baixa"
    RUIDO = "ruido"


@dataclass(frozen=True)
class EmailEntity:
    id: str
    provider: str
    account_id: str
    account_email: str
    thread_id: str | None
    subject: str
    sender: str
    recipients: list[str]
    snippet: str
    labels: list[str] = field(default_factory=list)
    received_at: str | None = None
    raw_headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}

    def to_work_item(self) -> "WorkItem":
        return WorkItem(
            id=f"{self.provider}:{self.id}",
            source=self.provider,
            type="email",
            account_id=self.account_id,
            payload=self.to_dict(),
        )


@dataclass(frozen=True)
class WorkItem:
    id: str
    source: str
    type: str
    account_id: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class Classification:
    category: Category
    priority: Priority
    confidence: float
    reason: str
    possible_event: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "possible_event": self.possible_event,
            "schema_version": SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class ActionPlan:
    type: str
    reason: str
    dry_run: bool
    status: str = "planned"
    payload: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    source: str = "automation_planner"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.id is None:
            object.__setattr__(self, "id", f"action:{self.type}:{uuid4().hex}")

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "schema_version": SCHEMA_VERSION}


@dataclass(frozen=True)
class PipelineResult:
    email: EmailEntity
    classification: Classification
    action_plans: list[ActionPlan]
    existed: bool = False
    work_item: WorkItem | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email.to_dict(),
            "work_item": self.work_item.to_dict() if self.work_item else None,
            "classification": self.classification.to_dict(),
            "action_plans": [action.to_dict() for action in self.action_plans],
            "existed": self.existed,
        }
