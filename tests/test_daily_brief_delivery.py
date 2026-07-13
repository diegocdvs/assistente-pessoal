from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from app.daily_brief.models import DailyBrief
from app.daily_brief_delivery import (
    DailyBriefDeliveryDoubleCheck,
    DailyBriefDeliveryPolicy,
    DailyBriefDeliveryRecord,
    DailyBriefDeliveryService,
    DailyBriefEmailRenderer,
    DeliveryPolicySettings,
    FirestoreDailyBriefDeliveryRepository,
    InMemoryDailyBriefDeliveryRepository,
)
from app.daily_brief_delivery.gmail import GmailDailyBriefDeliveryClient, _encode_message
from scripts import daily_brief_delivery


def test_email_message_renders_text_html_subject_and_idempotency():
    brief = sample_brief(status="WARNING", headline="<script>alert(1)</script>")

    message = DailyBriefEmailRenderer().render(brief, account_id="pessoal_google", recipient="user@example.com", mode="draft")

    assert message.subject == "Daily Brief - Atencao necessaria - 2026-07-10"
    assert "DAILY BRIEF" in message.text_body
    assert "&lt;script&gt;" in message.html_body
    assert "<script>" not in message.html_body
    assert message.to_dict().get("html_body") is None
    assert message.idempotency_key == DailyBriefEmailRenderer().render(
        brief,
        account_id="pessoal_google",
        recipient="USER@example.com",
        mode="draft",
    ).idempotency_key


def test_policy_blocks_disabled_and_recipient_outside_allowlist():
    brief = sample_brief()
    policy = DailyBriefDeliveryPolicy()

    disabled = policy.evaluate(
        brief,
        settings=DeliveryPolicySettings(enabled=False, mode="draft", recipients=("user@example.com",), timezone="UTC"),
        recipient="user@example.com",
        mode="draft",
        now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
    )
    outside = policy.evaluate(
        brief,
        settings=DeliveryPolicySettings(enabled=True, mode="draft", recipients=("allowed@example.com",), timezone="UTC"),
        recipient="other@example.com",
        mode="draft",
        now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
    )

    assert disabled.decision == "BLOCK"
    assert disabled.effective_mode == "disabled"
    assert outside.reason == "recipient outside allowlist"


def test_policy_allows_draft_and_requires_explicit_send():
    brief = sample_brief()
    policy = DailyBriefDeliveryPolicy()
    settings = DeliveryPolicySettings(enabled=True, mode="draft", recipients=("user@example.com",), timezone="UTC")

    draft = policy.evaluate(brief, settings=settings, recipient="user@example.com", mode="draft", now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc))
    send_blocked = policy.evaluate(brief, settings=settings, recipient="user@example.com", mode="send", now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc))
    send_allowed = policy.evaluate(
        brief,
        settings=DeliveryPolicySettings(enabled=True, mode="send", recipients=("user@example.com",), allow_send=True, timezone="UTC"),
        recipient="user@example.com",
        mode="send",
        now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
    )

    assert draft.decision == "ALLOW_DRAFT"
    assert send_blocked.reason == "send mode requires explicit allow_send"
    assert send_allowed.decision == "ALLOW_SEND"


def test_policy_review_for_risk_discrepancy_or_window_and_block_error():
    policy = DailyBriefDeliveryPolicy()
    settings = DeliveryPolicySettings(enabled=True, mode="send", recipients=("user@example.com",), allow_send=True, timezone="UTC")

    assert policy.evaluate(
        sample_brief(open_discrepancies=[{"id": "d"}]),
        settings=settings,
        recipient="user@example.com",
        mode="send",
        now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
    ).decision == "REVIEW"
    assert policy.evaluate(
        sample_brief(high_risk_items=[{"id": "risk"}]),
        settings=settings,
        recipient="user@example.com",
        mode="send",
        now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
    ).reason == "high risk items require review before send"
    assert policy.evaluate(
        sample_brief(status="ERROR"),
        settings=settings,
        recipient="user@example.com",
        mode="send",
        now=datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
    ).reason == "brief status ERROR blocks delivery"
    assert policy.evaluate(
        sample_brief(),
        settings=settings,
        recipient="user@example.com",
        mode="send",
        now=datetime(2026, 7, 10, 14, tzinfo=timezone.utc),
    ).reason == "outside configured delivery window"


def test_service_dry_run_idempotency_and_force():
    repo = InMemoryDailyBriefDeliveryRepository()
    client = Mock()
    settings = DeliveryPolicySettings(enabled=True, mode="draft", recipients=("user@example.com",), timezone="UTC")
    service = DailyBriefDeliveryService(repository=repo, client=client)
    now = datetime(2026, 7, 10, 8, tzinfo=timezone.utc)

    first = service.deliver(sample_brief(), account_id="pessoal_google", recipient="user@example.com", mode="draft", settings=settings, dry_run=True, now=now)
    second = service.deliver(sample_brief(), account_id="pessoal_google", recipient="user@example.com", mode="draft", settings=settings, dry_run=True, now=now)
    forced = service.deliver(sample_brief(), account_id="pessoal_google", recipient="user@example.com", mode="draft", settings=settings, dry_run=True, force=True, now=now)

    assert first.status == "skipped"
    assert second.metadata["existing_delivery_id"] == first.delivery_id
    assert forced.policy_decision == "ALLOW_DRAFT"
    client.create_draft.assert_not_called()


def test_service_creates_draft_and_sends_with_mock_client():
    settings = DeliveryPolicySettings(enabled=True, mode="draft", recipients=("user@example.com",), allow_send=True, timezone="UTC")
    client = Mock()
    client.create_draft.return_value = {"id": "draft-1"}
    client.send_message.return_value = {"id": "message-1"}
    service = DailyBriefDeliveryService(repository=InMemoryDailyBriefDeliveryRepository(), client=client)
    now = datetime(2026, 7, 10, 8, tzinfo=timezone.utc)

    draft = service.deliver(sample_brief(), account_id="pessoal_google", recipient="user@example.com", mode="draft", settings=settings, dry_run=False, now=now)
    sent = service.deliver(sample_brief(), account_id="pessoal_google", recipient="user@example.com", mode="send", settings=settings, dry_run=False, force=True, now=now)

    assert draft.status == "draft_created"
    assert draft.gmail_draft_id == "draft-1"
    assert sent.status == "sent"
    assert sent.gmail_message_id == "message-1"


def test_gmail_delivery_client_uses_drafts_and_messages_without_real_api():
    service = Mock()
    service.users.return_value.drafts.return_value.create.return_value.execute.return_value = {"id": "draft-1"}
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "msg-1"}
    client = GmailDailyBriefDeliveryClient(project_id="project", secret_prefix="google-pessoal", service=service, secret_reader=Mock())
    message = DailyBriefEmailRenderer().render(sample_brief(), account_id="pessoal_google", recipient="user@example.com", mode="draft")

    assert client.create_draft(message)["id"] == "draft-1"
    assert client.send_message(message)["id"] == "msg-1"
    raw = _encode_message(message)

    assert isinstance(raw, str)
    service.users.return_value.drafts.return_value.create.assert_called_once()
    service.users.return_value.messages.return_value.send.assert_called_once()


def test_firestore_delivery_repository_collection_and_lookup():
    client = Mock()
    doc = Mock()
    doc.to_dict.return_value = sample_record().to_dict()
    client.collection.return_value.where.return_value.limit.return_value.stream.return_value = [doc]
    with patch("app.daily_brief_delivery.repository.firestore.Client", return_value=client):
        repo = FirestoreDailyBriefDeliveryRepository("project")
        repo.save(sample_record())
        found = repo.find_by_idempotency_key("key")

    assert found.delivery_id == "delivery:key"
    client.collection.assert_called_with("daily_brief_deliveries")


def test_delivery_double_check_flags_inconsistent_success():
    findings = DailyBriefDeliveryDoubleCheck().inspect([
        sample_record(mode="send", status="sent", policy_decision="ALLOW_DRAFT"),
        sample_record(status="draft_created", error="boom"),
    ])

    assert {finding.type for finding in findings} == {
        "delivery_sent_without_allow_send_policy",
        "successful_delivery_with_error",
    }


def test_cli_help_and_disabled_mode(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        daily_brief_delivery.main_with_args(["--help"])
    assert exc.value.code == 0
    capsys.readouterr()

    class FakeBriefRepository:
        def __init__(self, *_args, **_kwargs):
            pass

        def latest(self):
            return sample_brief()

        def save(self, brief):
            return brief.brief_id

    monkeypatch.setattr(daily_brief_delivery, "FirestoreDailyBriefRepository", FakeBriefRepository)
    monkeypatch.setattr(daily_brief_delivery, "FirestoreDailyBriefDeliveryRepository", lambda *_args, **_kwargs: InMemoryDailyBriefDeliveryRepository())

    assert daily_brief_delivery.main_with_args(["--use-last-brief", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "skipped"
    assert payload["mode"] == "disabled"


def sample_record(**overrides):
    data = {
        "delivery_id": "delivery:key",
        "brief_id": "brief",
        "account_id": "pessoal_google",
        "recipient": "user@example.com",
        "mode": "draft",
        "policy_decision": "ALLOW_DRAFT",
        "policy_reason": "ok",
        "status": "skipped",
        "idempotency_key": "key",
    }
    data.update(overrides)
    return DailyBriefDeliveryRecord(**data)


def sample_brief(**overrides):
    data = {
        "brief_id": "daily-brief:2026-07-10:all",
        "date": "2026-07-10",
        "timezone": "UTC",
        "generated_at": "2026-07-10T08:00:00+00:00",
        "account_ids": ["pessoal_google"],
        "status": "OK",
        "headline": "Dia tranquilo.",
        "agenda_today": [{"title": "Reuniao", "start_at": "2026-07-10T09:00:00+00:00"}],
        "agenda_tomorrow": [],
        "next_event": None,
        "free_windows_today": [],
        "calendar_conflicts": [],
        "critical_emails": [],
        "top_priorities": [],
        "followups": [],
        "pending_action_plans": [],
        "subscriptions_recommended": [],
        "subscriptions_waiting_approval": 0,
        "security_warnings": [],
        "high_risk_items": [],
        "last_audit_status": "OK",
        "last_audit_at": None,
        "open_discrepancies": [],
        "summary_metrics": {"meetings_today": 1, "critical_emails_count": 0, "conflicts_count": 0, "followups_count": 0},
        "sections": [],
    }
    data.update(overrides)
    return DailyBrief(**data)
