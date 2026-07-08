from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.connectors.manager import ConnectorManager
from app.core.accounts import AccountManager, MailAccount
from app.core.automation import AutomationPlanner
from app.core.classifier import RuleBasedClassifier
from app.core.interfaces import (
    AutomationPlannerProtocol,
    ClassifierProtocol,
    ConnectorManagerProtocol,
    PersistenceProtocol,
    ReporterProtocol,
)
from app.core.models import PipelineResult
from app.core.report import Reporter
from app.storage.persistence import FirestorePersistence

logger = logging.getLogger(__name__)


class DailyJob:
    def __init__(
        self,
        settings: Settings,
        account_manager: AccountManager | None = None,
        connector_manager: ConnectorManagerProtocol | None = None,
        classifier: ClassifierProtocol | None = None,
        persistence: PersistenceProtocol | None = None,
        automation_planner: AutomationPlannerProtocol | None = None,
        reporter: ReporterProtocol | None = None,
    ) -> None:
        self.settings = settings
        self.account_manager = account_manager or AccountManager(settings.accounts_config_path)
        self.connector_manager = connector_manager or ConnectorManager.default(settings.project_id)
        self.classifier = classifier or RuleBasedClassifier()
        self.persistence = persistence or FirestorePersistence(settings.project_id)
        self.automation_planner = automation_planner or AutomationPlanner(dry_run=settings.dry_run)
        self.reporter = reporter or Reporter()

    def run(self) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        accounts = self.account_manager.enabled_accounts()
        results: list[PipelineResult] = []
        errors: list[dict[str, str]] = []

        logger.info("Processando %s contas habilitadas.", len(accounts))
        for account in accounts:
            try:
                results.extend(self._process_account(account))
            except Exception as exc:
                logger.exception("Falha ao processar conta %s", account.id)
                errors.append({"account_id": account.id, "provider": account.provider, "error": str(exc)})

        finished_at = datetime.now(timezone.utc)
        report = self.reporter.build(
            started_at=started_at,
            finished_at=finished_at,
            dry_run=self.settings.dry_run,
            accounts=accounts,
            results=results,
            errors=errors,
        )
        self.persistence.save_run(report)
        return report

    def _process_account(self, account: MailAccount) -> list[PipelineResult]:
        emails = self.connector_manager.fetch_recent(account)
        results: list[PipelineResult] = []

        for email in emails:
            classification = self.classifier.classify(email)
            action_plans = self.automation_planner.plan(email, classification)
            persistence_result = self.persistence.save_email(email)
            self.persistence.save_classification(email, classification)
            for action_plan in action_plans:
                self.persistence.save_action_plan(email, action_plan)
            results.append(PipelineResult(email, classification, action_plans, existed=persistence_result.existed))

        return results
