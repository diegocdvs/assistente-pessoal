from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.connectors.gmail import GmailConnector
from app.core.accounts import AccountManager, MailAccount
from app.core.classifier import classify_email
from app.core.models import ProcessedEmail, Priority
from app.storage.firestore_store import FirestoreStore

logger = logging.getLogger(__name__)


class DailyJob:
    def __init__(
        self,
        settings: Settings,
        account_manager: AccountManager | None = None,
        gmail_connector: GmailConnector | None = None,
        store: FirestoreStore | None = None,
    ) -> None:
        self.settings = settings
        self.account_manager = account_manager or AccountManager(settings.accounts_config_path)
        self.gmail_connector = gmail_connector or GmailConnector(settings.project_id)
        self.store = store or FirestoreStore(settings.project_id)

    def run(self) -> dict[str, Any]:
        accounts = self.account_manager.enabled_accounts()
        processed: list[ProcessedEmail] = []
        errors: list[dict[str, str]] = []

        logger.info("Processando %s contas habilitadas.", len(accounts))
        for account in accounts:
            try:
                account_processed = self._process_account(account)
                processed.extend(account_processed)
                if account.firestore_enabled:
                    self.store.save_processed_emails(account_processed)
            except Exception as exc:
                logger.exception("Falha ao processar conta %s", account.id)
                errors.append({"account_id": account.id, "provider": account.provider, "error": str(exc)})

        report = self._build_report(accounts, processed, errors)
        self.store.save_run(report)
        return report

    def _process_account(self, account: MailAccount) -> list[ProcessedEmail]:
        if account.provider == "gmail":
            emails = self.gmail_connector.fetch_recent(account)
        else:
            raise NotImplementedError(f"Provider ainda nao suportado nesta sprint: {account.provider}")

        processed: list[ProcessedEmail] = []
        for email in emails:
            classification = classify_email(email)
            actions = self._planned_actions(classification)
            processed.append(ProcessedEmail(email, classification, actions))
        return processed

    def _planned_actions(self, classification: Any) -> list[str]:
        actions: list[str] = []
        if classification.possible_event:
            actions.append("registrar possivel evento para revisao futura")
        if classification.priority == Priority.CRITICA:
            actions.append("destacar como alerta critico no relatorio")
        return actions

    def _build_report(
        self,
        accounts: list[MailAccount],
        processed: list[ProcessedEmail],
        errors: list[dict[str, str]],
    ) -> dict[str, Any]:
        important = [p.to_dict() for p in processed if p.classification.priority in {Priority.CRITICA, Priority.IMPORTANTE}]
        noise = [p.to_dict() for p in processed if p.classification.priority == Priority.RUIDO]
        informative = [p.to_dict() for p in processed if p.classification.priority == Priority.INFORMATIVA]

        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": self.settings.dry_run,
            "accounts_total": len(accounts),
            "accounts": [
                {
                    "id": account.id,
                    "label": account.label,
                    "provider": account.provider,
                    "email": account.email,
                    "max_emails": account.max_emails,
                }
                for account in accounts
            ],
            "total": len(processed),
            "important_count": len(important),
            "noise_count": len(noise),
            "informative_count": len(informative),
            "errors": errors,
            "important": important,
            "noise": noise,
            "informative": informative,
        }
