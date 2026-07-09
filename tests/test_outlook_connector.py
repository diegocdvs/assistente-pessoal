from __future__ import annotations

from app.connectors.outlook import OutlookAccount, OutlookConfig, OutlookConnector, OutlookNormalizer
from app.core.accounts import MailAccount


def make_account() -> MailAccount:
    return MailAccount(
        id="outlook_profissional",
        label="Outlook Profissional",
        provider="outlook",
        email="profissional@example.com",
        enabled=False,
        secret_prefix="outlook-profissional",
        max_emails=10,
    )


def fake_graph_message() -> dict:
    return {
        "id": "AAMkAGI2",
        "conversationId": "AAQkAGI2-thread",
        "changeKey": "CQAAABYAA",
        "internetMessageId": "<message@example.com>",
        "subject": "Invoice approved",
        "bodyPreview": "Your invoice was approved.",
        "receivedDateTime": "2026-07-09T12:30:00Z",
        "importance": "normal",
        "isRead": False,
        "webLink": "https://outlook.office.com/mail/id/AAMkAGI2",
        "categories": ["Financeiro"],
        "from": {
            "emailAddress": {
                "name": "Finance Team",
                "address": "finance@example.com",
            }
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "name": "User",
                    "address": "profissional@example.com",
                }
            }
        ],
        "ccRecipients": [
            {
                "emailAddress": {
                    "address": "copy@example.com",
                }
            }
        ],
        "internetMessageHeaders": [
            {"name": "Message-ID", "value": "<message@example.com>"},
            {"name": "x-ms-exchange-organization-authas", "value": "Internal"},
        ],
    }


def test_outlook_account_is_derived_from_mail_account():
    account = OutlookAccount.from_mail_account(
        make_account(),
        OutlookConfig(tenant_id="tenant", client_id_secret_name="client-id"),
    )

    assert account.account_id == "outlook_profissional"
    assert account.email == "profissional@example.com"
    assert account.secret_prefix == "outlook-profissional"
    assert account.config.tenant_id == "tenant"
    assert account.config.scopes == ("Mail.Read", "offline_access")


def test_outlook_normalizer_converts_graph_payload_to_email_entity_and_work_item():
    email = OutlookNormalizer().to_email_entity(make_account(), fake_graph_message())

    assert email.id == "AAMkAGI2"
    assert email.provider == "outlook"
    assert email.account_id == "outlook_profissional"
    assert email.account_email == "profissional@example.com"
    assert email.thread_id == "AAQkAGI2-thread"
    assert email.subject == "Invoice approved"
    assert email.sender == "Finance Team <finance@example.com>"
    assert email.recipients == ["User <profissional@example.com>", "copy@example.com"]
    assert email.snippet == "Your invoice was approved."
    assert email.labels == ["Financeiro"]
    assert email.received_at == "2026-07-09T12:30:00Z"
    assert email.raw_headers["message-id"] == "<message@example.com>"
    assert email.metadata["outlook_is_read"] is False
    assert email.metadata["outlook_importance"] == "normal"

    work_item = email.to_work_item()
    assert work_item.id == "outlook:AAMkAGI2"
    assert work_item.source == "outlook"
    assert work_item.type == "email"
    assert work_item.payload["provider"] == "outlook"


def test_outlook_connector_stub_is_disabled_by_default():
    connector = OutlookConnector(graph_messages=[fake_graph_message()])

    assert connector.fetch_recent(make_account()) == []


def test_outlook_connector_can_normalize_fake_payloads_without_graph_calls():
    connector = OutlookConnector(enabled=True, graph_messages=[fake_graph_message()])

    emails = connector.fetch_recent(make_account())

    assert len(emails) == 1
    assert emails[0].provider == "outlook"
    assert emails[0].id == "AAMkAGI2"
