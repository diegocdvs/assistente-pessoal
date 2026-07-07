from __future__ import annotations

from app.connectors.gmail import GmailConnector
from app.core.accounts import MailAccount


def test_gmail_payload_is_converted_to_email_item():
    connector = GmailConnector(project_id="project", secret_reader=object())
    account = MailAccount(
        id="pessoal",
        label="Pessoal",
        provider="gmail",
        email="pessoal@example.com",
        enabled=True,
        secret_prefix="google-pessoal",
    )

    email = connector._to_email_item(
        account,
        {
            "id": "abc123",
            "threadId": "thread123",
            "snippet": "Resumo da mensagem",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Remetente <r@example.com>"},
                    {"name": "To", "value": "pessoal@example.com"},
                    {"name": "Subject", "value": "=?utf-8?q?Ola?="},
                    {"name": "Date", "value": "Tue, 07 Jul 2026 10:00:00 -0300"},
                ]
            },
        },
    )

    assert email.account_id == "pessoal"
    assert email.provider == "gmail"
    assert email.id == "abc123"
    assert email.subject == "Ola"
    assert email.labels == ["INBOX", "UNREAD"]
    assert email.received_at is not None
