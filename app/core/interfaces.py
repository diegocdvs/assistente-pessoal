from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.core.accounts import MailAccount
from app.core.models import ActionPlan, Classification, EmailEntity, PipelineResult
from app.storage.persistence import PersistenceResult


class ConnectorManagerProtocol(Protocol):
    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        pass


class ClassifierProtocol(Protocol):
    def classify(self, email: EmailEntity) -> Classification:
        pass


class PersistenceProtocol(Protocol):
    def save_run(self, report: dict[str, Any]) -> str:
        pass

    def save_email(self, email: EmailEntity) -> PersistenceResult:
        pass

    def save_classification(self, email: EmailEntity, classification: Classification) -> str:
        pass

    def save_action_plan(self, email: EmailEntity, action_plan: ActionPlan) -> str:
        pass


class AutomationPlannerProtocol(Protocol):
    def plan(self, email: EmailEntity, classification: Classification) -> list[ActionPlan]:
        pass


class ReporterProtocol(Protocol):
    def build(
        self,
        *,
        started_at: datetime,
        finished_at: datetime,
        dry_run: bool,
        accounts: list[MailAccount],
        results: list[PipelineResult],
        errors: list[dict[str, str]],
    ) -> dict[str, Any]:
        pass
