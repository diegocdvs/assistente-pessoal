from __future__ import annotations

from app.core.models import EmailEntity, WorkItem


def test_email_entity_serializes_normalized_fields():
    email = EmailEntity(
        id="msg-1",
        provider="gmail",
        account_id="acc",
        account_email="acc@example.com",
        thread_id="thread-1",
        subject="Assunto",
        sender="sender@example.com",
        recipients=["acc@example.com"],
        snippet="Resumo",
        labels=["INBOX"],
        received_at="2026-07-08T10:00:00Z",
        raw_headers={"subject": "Assunto"},
        metadata={"history_id": "123"},
    )

    payload = email.to_dict()

    assert payload["id"] == "msg-1"
    assert payload["provider"] == "gmail"
    assert payload["metadata"] == {"history_id": "123"}


def test_work_item_serializes_generic_payload():
    item = WorkItem(
        id="work-1",
        source="gmail",
        type="email",
        account_id="acc",
        payload={"email_id": "msg-1"},
    )

    payload = item.to_dict()

    assert payload["id"] == "work-1"
    assert payload["payload"] == {"email_id": "msg-1"}
    assert payload["created_at"]
