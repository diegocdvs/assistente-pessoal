from __future__ import annotations

from app.core.models import ActionPlan, EmailEntity, WorkItem


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
    assert payload["schema_version"] == "0.2"


def test_email_entity_converts_to_work_item():
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
    )

    item = email.to_work_item()

    assert item.id == "gmail:msg-1"
    assert item.source == "gmail"
    assert item.type == "email"
    assert item.account_id == "acc"
    assert item.payload["id"] == "msg-1"
    assert item.payload["schema_version"] == "0.2"


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
    assert payload["schema_version"] == "0.2"


def test_action_plan_has_audit_fields_and_keeps_compatible_constructor():
    plan = ActionPlan("review_financial", "Revisar.", True, payload={"email_id": "msg-1"})

    payload = plan.to_dict()

    assert payload["type"] == "review_financial"
    assert payload["reason"] == "Revisar."
    assert payload["dry_run"] is True
    assert payload["status"] == "planned"
    assert payload["id"].startswith("action:review_financial:")
    assert payload["source"] == "automation_planner"
    assert payload["created_at"]
    assert payload["updated_at"]
    assert payload["audit_metadata"] == {}
    assert payload["schema_version"] == "0.2"
