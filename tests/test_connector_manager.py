from __future__ import annotations

import pytest

from app.connectors import manager as manager_module
from app.connectors.manager import ConnectorManager, ConnectorNotSupportedError
from app.connectors.outlook import OutlookConnector
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


def test_default_connector_manager_registers_gmail_and_disabled_outlook(monkeypatch):
    monkeypatch.setattr(manager_module, "GmailConnector", lambda project_id: FakeConnector())

    manager = ConnectorManager.default("project")

    assert manager.supported_providers() == ["gmail", "outlook"]


def test_default_connector_manager_can_enable_outlook(monkeypatch):
    class FakeOAuthProvider:
        def __init__(self, *, secret_reader):
            self.secret_reader = secret_reader

        def get_access_token(self, account):
            return "token-123"

    class FakeMessageClient:
        def fetch_recent_messages(self, *, access_token, max_results):
            return [
                {
                    "id": "outlook-msg-1",
                    "subject": "Outlook",
                    "from": {"emailAddress": {"address": "sender@example.com"}},
                    "toRecipients": [{"emailAddress": {"address": "acc@example.com"}}],
                }
            ]

    monkeypatch.setattr(manager_module, "GmailConnector", lambda project_id: FakeConnector())
    monkeypatch.setattr(manager_module, "SecretReader", lambda project_id: object())
    monkeypatch.setattr(manager_module, "MicrosoftOAuthProvider", FakeOAuthProvider)
    monkeypatch.setattr(manager_module, "MicrosoftGraphMailClient", FakeMessageClient)

    manager = ConnectorManager.default("project", outlook_enabled=True)

    emails = manager.fetch_recent(make_account("outlook"))
    assert manager.supported_providers() == ["gmail", "outlook"]
    assert len(emails) == 1
    assert emails[0].provider == "outlook"


def test_connector_manager_routes_to_outlook_stub_when_registered():
    manager = ConnectorManager()
    manager.register(OutlookConnector(enabled=False))

    assert manager.fetch_recent(make_account("outlook")) == []
