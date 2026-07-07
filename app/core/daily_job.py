from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.core.classifier import classify_email
from app.core.models import EmailItem, ProcessedEmail, Priority
from app.storage.firestore_store import FirestoreStore

logger = logging.getLogger(__name__)


class DailyJob:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = FirestoreStore(settings.project_id)

    def run(self) -> dict[str, Any]:
        # MVP: no primeiro deploy, evitamos tocar nas caixas até os tokens estarem validados.
        # Os conectores reais entram na próxima iteração, usando os secrets do Secret Manager.
        emails = self._load_placeholder_emails()
        processed: list[ProcessedEmail] = []

        for email in emails:
            classification = classify_email(email)
            actions = self._planned_actions(classification)
            processed.append(ProcessedEmail(email, classification, actions))

        report = self._build_report(processed)
        self.store.save_run(report)
        return report

    def _load_placeholder_emails(self) -> list[EmailItem]:
        logger.info("MVP placeholder ativo; conectores Gmail/Outlook serão ligados após bootstrap dos tokens.")
        return []

    def _planned_actions(self, classification) -> list[str]:
        actions: list[str] = []
        if classification.possible_event:
            actions.append("DRY_RUN: simular criação de evento na Google Agenda")
        if classification.should_mark_read:
            actions.append("DRY_RUN: simular marcação como lido")
        if classification.priority == Priority.CRITICA:
            actions.append("DRY_RUN: alertar imediatamente")
        return actions

    def _build_report(self, processed: list[ProcessedEmail]) -> dict[str, Any]:
        important = [p.to_dict() for p in processed if p.classification.priority in {Priority.CRITICA, Priority.IMPORTANTE}]
        noise = [p.to_dict() for p in processed if p.classification.priority == Priority.RUIDO]
        informative = [p.to_dict() for p in processed if p.classification.priority == Priority.INFORMATIVA]

        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": self.settings.dry_run,
            "total": len(processed),
            "important_count": len(important),
            "noise_count": len(noise),
            "informative_count": len(informative),
            "important": important,
            "noise": noise,
            "informative": informative,
        }
