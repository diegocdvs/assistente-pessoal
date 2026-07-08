from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.connectors.gmail import GmailConnector
from app.core.accounts import AccountManager, MailAccount
from app.core.automation import AutomationPlanner
from app.core.classifier import RuleBasedClassifier
from app.core.models import EmailEntity, PipelineResult
from app.core.report import ReportBuilder
from app.storage.persistence import FirestorePersistence

logger = logging.getLogger(__name__)


class DailyJob:
    def __init__(
        self,
        settings: Settings,
        account_manager: AccountManager | None = None,
        gmail_connector: GmailConnector | None = None,
        classifier: RuleBasedClassifier | None = None,
        persistence: FirestorePersistence | None = None,
        automation_planner: AutomationPlanner | None = None,
        report_builder: ReportBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.account_manager = account_manager or AccountManager(settings.accounts_config_path)
        self.gmail_connector = gmail_connector or GmailConnector(settings.project_id)
        self.classifier = classifier or RuleBasedClassifier()
        self.persistence = persistence or FirestorePersistence(settings.project_id)
        self.automation_planner = automation_planner or AutomationPlanner(dry_run=settings.dry_run)
        self.report_builder = report_builder or ReportBuilder()

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

        report = self.report_builder.build(
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            dry_run=self.settings.dry_run,
            accounts=accounts,
            results=results,
            errors=errors,
        )
        self.persistence.save_run(report)
        return report

    def _process_account(self, account: MailAccount) -> list[PipelineResult]:
        emails = self._fetch_emails(account)
        results: list[PipelineResult] = []

        for email in emails:
            classification = self.classifier.classify(email)
            actions = self.automation_planner.plan(email, classification)
            persistence_result = self.persistence.upsert_email(email, classification, actions)
            results.append(PipelineResult(email, classification, actions, existed=persistence_result.existed))

        return results

    def _fetch_emails(self, account: MailAccount) -> list[EmailEntity]:
        if account.provider == "gmail":
            return self.gmail_connector.fetch_recent(account)
        raise NotImplementedError(f"Provider ainda nao suportado nesta sprint: {account.provider}")
