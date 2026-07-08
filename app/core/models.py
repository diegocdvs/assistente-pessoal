from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


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
        return asdict(self)


@dataclass(frozen=True)
class Classification:
    category: Category
    priority: Priority
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "priority": self.priority.value,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ActionPlan:
    type: str
    reason: str
    dry_run: bool
    status: str = "planned"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PipelineResult:
    email: EmailEntity
    classification: Classification
    actions: list[ActionPlan]
    existed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email.to_dict(),
            "classification": self.classification.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "existed": self.existed,
        }
