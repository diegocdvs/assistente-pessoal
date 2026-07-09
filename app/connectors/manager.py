from __future__ import annotations

from app.auth.microsoft import MicrosoftOAuthProvider
from app.connectors.base import Connector
from app.connectors.gmail import GmailConnector
from app.connectors.secrets import SecretReader
from app.connectors.outlook import OutlookConnector
from app.core.accounts import MailAccount
from app.core.models import EmailEntity
from app.integrations.microsoft_graph import MicrosoftGraphMailClient


class ConnectorNotSupportedError(NotImplementedError):
    pass


class ConnectorManager:
    PLANNED_PROVIDERS = ("gmail", "outlook", "calendar", "whatsapp")

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    @classmethod
    def default(cls, project_id: str, *, outlook_enabled: bool = False) -> ConnectorManager:
        manager = cls()
        manager.register("gmail", GmailConnector(project_id))
        if outlook_enabled:
            secret_reader = SecretReader(project_id)
            manager.register(
                OutlookConnector(
                    enabled=True,
                    oauth_provider=MicrosoftOAuthProvider(secret_reader=secret_reader),
                    message_client=MicrosoftGraphMailClient(),
                )
            )
        else:
            manager.register(OutlookConnector(enabled=False))
        return manager

    def register(self, provider: str | Connector, connector: Connector | None = None) -> None:
        if connector is None:
            connector = provider
            provider = connector.provider
        if not isinstance(provider, str):
            raise TypeError("provider deve ser string ou connector deve expor provider.")
        self._connectors[provider] = connector

    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        connector = self._connectors.get(account.provider)
        if connector is None:
            raise ConnectorNotSupportedError(f"Provider ainda nao suportado: {account.provider}")
        return connector.fetch_recent(account)

    def supported_providers(self) -> list[str]:
        return sorted(self._connectors)
