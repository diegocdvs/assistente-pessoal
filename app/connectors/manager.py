from __future__ import annotations

from typing import Protocol

from app.connectors.gmail import GmailConnector
from app.core.accounts import MailAccount
from app.core.models import EmailEntity


class EmailConnector(Protocol):
    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        pass


class ConnectorNotSupportedError(NotImplementedError):
    pass


class ConnectorManager:
    PLANNED_PROVIDERS = ("gmail", "outlook", "calendar", "whatsapp")

    def __init__(self) -> None:
        self._connectors: dict[str, EmailConnector] = {}

    @classmethod
    def default(cls, project_id: str) -> ConnectorManager:
        manager = cls()
        manager.register("gmail", GmailConnector(project_id))
        return manager

    def register(self, provider: str, connector: EmailConnector) -> None:
        self._connectors[provider] = connector

    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        connector = self._connectors.get(account.provider)
        if connector is None:
            raise ConnectorNotSupportedError(f"Provider ainda nao suportado: {account.provider}")
        return connector.fetch_recent(account)

    def supported_providers(self) -> list[str]:
        return sorted(self._connectors)
