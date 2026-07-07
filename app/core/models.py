from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class Category(str, Enum):
    PROMOCOES = "promocoes"
    NEWSLETTER = "newsletter"
    FINANCEIRO = "financeiro"
    TRABALHO = "trabalho"
    EVENTO = "evento"
    COMPRA = "compra"
    SECURITY = "security"
    OUTROS = "outros"


class Priority(str, Enum):
    CRITICA = "critica"
    IMPORTANTE = "importante"
    INFORMATIVA = "informativa"
    RUIDO = "ruido"


@dataclass
class EmailItem:
    provider: str
    id: str
    subject: str
    sender: str
    snippet: str
    received_at: str | None = None


@dataclass
class Classification:
    category: Category
    priority: Priority
    reason: str
    should_mark_read: bool = False
    possible_event: bool = False


@dataclass
class ProcessedEmail:
    email: EmailItem
    classification: Classification
    actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": asdict(self.email),
            "classification": {
                "category": self.classification.category.value,
                "priority": self.classification.priority.value,
                "reason": self.classification.reason,
                "should_mark_read": self.classification.should_mark_read,
                "possible_event": self.classification.possible_event,
            },
            "actions": self.actions,
        }
