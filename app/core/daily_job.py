from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

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
        run_id = f"run-{uuid4().hex}"
        started_at = datetime.now(timezone.utc)
        accounts = self.account_manager.enabled_accounts()
        results: list[PipelineResult] = []
        errors: list[dict[str, str]] = []
        stage_counts = {
            "accounts_enabled": len(accounts),
            "emails_fetched": 0,
            "work_items_created": 0,
            "classifications_created": 0,
            "action_plans_created": 0,
            "errors": 0,
        }

        logger.info("run_id=%s event=job_started accounts_enabled=%s", run_id, len(accounts))
        for account in accounts:
            try:
                account_results = self._process_account(account, run_id)
                results.extend(account_results)
                stage_counts["emails_fetched"] += len(account_results)
                stage_counts["work_items_created"] += len(account_results)
                stage_counts["classifications_created"] += len(account_results)
                stage_counts["action_plans_created"] += sum(len(result.action_plans) for result in account_results)
                logger.info(
                    "run_id=%s event=account_processed account_id=%s provider=%s emails=%s action_plans=%s",
                    run_id,
                    account.id,
                    account.provider,
                    len(account_results),
                    sum(len(result.action_plans) for result in account_results),
                )
            except Exception as exc:
                logger.exception("run_id=%s event=account_failed account_id=%s provider=%s", run_id, account.id, account.provider)
                errors.append({"account_id": account.id, "provider": account.provider, "error": str(exc)})
                stage_counts["errors"] += 1

        finished_at = datetime.now(timezone.utc)
        report = self.reporter.build(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            dry_run=self.settings.dry_run,
            accounts=accounts,
            results=results,
            errors=errors,
            stage_counts=stage_counts,
        )
        self.persistence.save_run(report)
        logger.info(
            "run_id=%s event=job_finished total=%s errors=%s duration_seconds=%s",
            run_id,
            report["total"],
            len(errors),
            report["duration_seconds"],
        )
        return report

    def _process_account(self, account: MailAccount, run_id: str) -> list[PipelineResult]:
        emails = self.connector_manager.fetch_recent(account)
        results: list[PipelineResult] = []

        for email in emails:
            work_item = email.to_work_item()
            classification = self.classifier.classify(email)
            action_plans = self.automation_planner.plan(email, classification)
            persistence_result = self.persistence.save_email(email, run_id=run_id)
            self.persistence.save_classification(email, classification, run_id=run_id)
            for action_plan in action_plans:
                self.persistence.save_action_plan(email, action_plan, run_id=run_id)
            results.append(
                PipelineResult(
                    email,
                    classification,
                    action_plans,
                    existed=persistence_result.existed,
                    work_item=work_item,
                )
            )

        return results
