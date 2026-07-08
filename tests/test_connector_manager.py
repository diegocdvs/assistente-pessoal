from __future__ import annotations

import pytest

from app.connectors.manager import ConnectorManager, ConnectorNotSupportedError
from app.core.accounts import MailAccount
from app.core.models import EmailEntity


class FakeConnector:
    def fetch_recent(self, account):
        return [
            EmailEntity(
                id="msg-1",
                provider=account.provider,
                account_id=account.id,
                account_email=account.email,
                thread_id=None,
                subject="Assunto",
                sender="sender@example.com",
                recipients=[account.email],
                snippet="Resumo",
            )
        ]


def make_account(provider: str = "gmail") -> MailAccount:
    return MailAccount(
        id="acc",
        label="Conta",
        provider=provider,
        email="acc@example.com",
        enabled=True,
        secret_prefix="secret",
    )


def test_connector_manager_routes_by_provider():
    manager = ConnectorManager()
    manager.register("gmail", FakeConnector())

    emails = manager.fetch_recent(make_account("gmail"))

    assert len(emails) == 1
    assert emails[0].provider == "gmail"
    assert manager.supported_providers() == ["gmail"]
    assert "outlook" in manager.PLANNED_PROVIDERS
    assert "calendar" in manager.PLANNED_PROVIDERS
    assert "whatsapp" in manager.PLANNED_PROVIDERS


def test_connector_manager_rejects_unsupported_provider():
    manager = ConnectorManager()

    with pytest.raises(ConnectorNotSupportedError):
        manager.fetch_recent(make_account("outlook"))
