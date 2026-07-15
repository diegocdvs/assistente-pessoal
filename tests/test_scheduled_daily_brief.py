from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.config import load_settings
from app.context.models import ContextSnapshot
from app.daily_brief import InMemoryDailyBriefRepository
from app.daily_brief_delivery import InMemoryDailyBriefDeliveryRepository
from app.daily_brief_delivery.service import DailyBriefDeliveryService
from app.scheduled_daily_brief import (
    InMemoryScheduledBriefRepository,
    ScheduledDailyBriefDoubleCheck,
    ScheduledDailyBriefRetryPolicy,
    ScheduledDailyBriefRun,
    ScheduledDailyBriefService,
    ScheduledDailyBriefSettings,
    build_scheduled_idempotency_key,
    hash_recipient,
    redact_recipient,
)
from app.scheduled_daily_brief.repository import FirestoreScheduledBriefRepository
from scripts import doctor, double_check, scheduled_daily_brief, smoke


def test_scheduled_run_model_serializes_and_validates():
    run = sample_run(status="pending")

    assert run.to_dict()["schema_version"]
    assert run.with_updates(status="running").status == "running"
    with pytest.raises(ValueError):
        sample_run(status="bad")


def test_schedule_settings_defaults_and_validation(monkeypatch):
    monkeypatch.setenv("PROJECT_ID", "project")
    settings = load_settings()

    assert settings.scheduled_daily_brief.enabled is False
    assert settings.scheduled_daily_brief.mode == "draft"
    ScheduledDailyBriefSettings(schedule_time="07:30", timezone="UTC").validate()
    with pytest.raises(ValueError):
        ScheduledDailyBriefSettings(schedule_time="27:99").validate()
    with pytest.raises(Exception):
        ScheduledDailyBriefSettings(timezone="Invalid/Zone").validate()


def test_idempotency_key_uses_date_timezone_scope_channel_mode_recipient_and_schema():
    first = build_scheduled_idempotency_key(
        schedule_date="2026-07-15",
        timezone_name="America/Sao_Paulo",
        account_scope="all",
        delivery_mode="draft",
        recipient="USER@example.com",
    )
    second = build_scheduled_idempotency_key(
        schedule_date="2026-07-15",
        timezone_name="America/Sao_Paulo",
        account_scope="all",
        delivery_mode="send",
        recipient="user@example.com",
    )

    assert first != second
    assert first == build_scheduled_idempotency_key(
        schedule_date="2026-07-15",
        timezone_name="America/Sao_Paulo",
        account_scope="all",
        delivery_mode="draft",
        recipient="user@example.com",
    )
    assert hash_recipient("user@example.com").startswith("recipient:")
    assert redact_recipient("user@example.com") == "us***@example.com"


def test_repository_acquire_prevents_duplicate_concurrent_runs():
    repo = InMemoryScheduledBriefRepository()
    run = sample_run()

    acquired, created = repo.acquire(run)
    duplicate, duplicate_created = repo.acquire(run.with_updates(run_id="other"))

    assert created is True
    assert duplicate_created is False
    assert duplicate.run_id == acquired.run_id


def test_firestore_repository_acquire_uses_transaction(monkeypatch):
    class FakeSnapshot:
        exists = False

    class FakeDoc:
        def get(self, transaction=None):
            return FakeSnapshot()

    class FakeCollection:
        def document(self, _key):
            return FakeDoc()

    class FakeTransaction:
        def __init__(self):
            self.set_calls = []

        def set(self, doc_ref, payload):
            self.set_calls.append((doc_ref, payload))

    class FakeClient:
        def __init__(self, *_, **__):
            self.tx = FakeTransaction()

        def collection(self, _name):
            return FakeCollection()

        def transaction(self):
            return self.tx

    monkeypatch.setattr("app.scheduled_daily_brief.repository.firestore.Client", lambda project: FakeClient())
    monkeypatch.setattr("app.scheduled_daily_brief.repository.firestore.transactional", lambda fn: fn)

    run, created = FirestoreScheduledBriefRepository("project").acquire(sample_run())

    assert created is True
    assert run.idempotency_key == sample_run().idempotency_key


def test_service_blocks_when_disabled_and_never_builds_context():
    context_engine = Mock()
    service = make_service(context_engine=context_engine)

    result = service.run(
        settings=ScheduledDailyBriefSettings(enabled=False, recipients=("user@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=False, recipients=("user@example.com",), timezone="UTC"),
        recipient="user@example.com",
        now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc),
    )

    assert result.run.status == "skipped"
    assert result.run.error_summary == "schedule disabled"
    context_engine.build_snapshot.assert_not_called()


def test_service_dry_run_skips_without_calling_delivery_client():
    client = Mock()
    service = make_service(client=client)

    result = service.run(
        settings=ScheduledDailyBriefSettings(enabled=True, recipients=("user@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=True, recipients=("user@example.com",), timezone="UTC"),
        recipient="user@example.com",
        dry_run=True,
        now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc),
    )

    assert result.run.status == "skipped"
    client.create_draft.assert_not_called()
    client.send_message.assert_not_called()


def test_service_creates_draft_and_send_requires_explicit_allow_send():
    draft_client = Mock()
    draft_client.create_draft.return_value = {"id": "draft-1"}
    draft = make_service(client=draft_client).run(
        settings=ScheduledDailyBriefSettings(enabled=True, mode="draft", recipients=("user@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=True, mode="draft", recipients=("user@example.com",), timezone="UTC"),
        recipient="user@example.com",
        dry_run=False,
        now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc),
    )
    blocked = make_service().run(
        settings=ScheduledDailyBriefSettings(enabled=True, mode="send", recipients=("user@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=True, mode="send", recipients=("user@example.com",), allow_send=False, timezone="UTC"),
        recipient="user@example.com",
        dry_run=False,
        now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc),
    )
    send_client = Mock()
    send_client.send_message.return_value = {"id": "msg-1"}
    sent = make_service(client=send_client).run(
        settings=ScheduledDailyBriefSettings(enabled=True, mode="send", recipients=("user@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=True, mode="send", recipients=("user@example.com",), allow_send=True, timezone="UTC"),
        recipient="user@example.com",
        dry_run=False,
        now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc),
    )

    assert draft.run.status == "draft_created"
    assert blocked.run.status == "blocked"
    assert sent.run.status == "delivered"


def test_service_skips_confirmed_delivery_even_with_force():
    repo = InMemoryScheduledBriefRepository()
    service = make_service(run_repository=repo)
    settings = ScheduledDailyBriefSettings(enabled=True, mode="draft", recipients=("user@example.com",), timezone="UTC")
    dsettings = delivery_settings(enabled=True, mode="draft", recipients=("user@example.com",), timezone="UTC")

    first = service.run(settings=settings, delivery_settings=dsettings, recipient="user@example.com", dry_run=True, now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc))
    repo.mark_draft_created(first.run, brief_id="brief", delivery_id="delivery")
    second = service.run(settings=settings, delivery_settings=dsettings, recipient="user@example.com", force=True, dry_run=True, now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc))

    assert second.run.status == "skipped"
    assert "confirmed delivery already exists" in second.run.error_summary


def test_service_blocks_recipient_outside_allowlist_and_outside_window():
    outside_recipient = make_service().run(
        settings=ScheduledDailyBriefSettings(enabled=True, recipients=("allowed@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=True, recipients=("allowed@example.com",), timezone="UTC"),
        recipient="other@example.com",
        now=datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc),
    )
    outside_window = make_service().run(
        settings=ScheduledDailyBriefSettings(enabled=True, schedule_time="07:30", lookback_hours=1, recipients=("user@example.com",), timezone="UTC"),
        delivery_settings=delivery_settings(enabled=True, recipients=("user@example.com",), timezone="UTC"),
        recipient="user@example.com",
        now=datetime(2026, 7, 15, 12, 30, tzinfo=timezone.utc),
    )

    assert outside_recipient.run.status == "blocked"
    assert outside_recipient.run.error_code == "recipient_outside_allowlist"
    assert outside_window.run.status == "blocked"
    assert outside_window.run.error_code == "outside_schedule_window"


def test_retry_policy_and_delivery_uncertain_no_retry():
    policy = ScheduledDailyBriefRetryPolicy(max_attempts=3)

    assert policy.classify(error_code="timeout", attempt=1).retryable is True
    assert policy.classify(error_code="missing_credentials", attempt=1).retryable is False
    assert policy.classify(error_code="timeout", attempt=3).retryable is False
    assert policy.classify(error_code="delivery_uncertain", attempt=1, possible_delivery=True).retryable is False


def test_double_check_reports_scheduled_inconsistencies():
    old = sample_run(status="running", started_at="2026-07-15T00:00:00+00:00")
    uncertain = sample_run(status="failed", error_code="delivery_uncertain")
    delivered = sample_run(status="delivered", delivery_id="missing")

    findings = ScheduledDailyBriefDoubleCheck().inspect(
        [old, uncertain, delivered, delivered.with_updates(run_id="duplicate")],
        delivery_ids=set(),
        scheduler_active=True,
        schedule_enabled=False,
        send_mode=True,
        allowlist_configured=False,
        now=datetime(2026, 7, 15, 5, tzinfo=timezone.utc),
    )

    types = {finding.type for finding in findings}
    assert "scheduled_run_stale_running" in types
    assert "scheduled_delivery_uncertain_requires_review" in types
    assert "scheduled_run_without_delivery_audit" in types
    assert "duplicate_scheduled_idempotency_key" in types
    assert "scheduler_active_with_feature_disabled" in types
    assert "scheduled_send_without_allowlist" in types


def test_cli_help_status_and_dry_run(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        scheduled_daily_brief.main_with_args(["--help"])
    assert exc.value.code == 0
    capsys.readouterr()

    monkeypatch.setattr(scheduled_daily_brief, "FirestoreScheduledBriefRepository", lambda *_args, **_kwargs: InMemoryScheduledBriefRepository())
    monkeypatch.setattr(scheduled_daily_brief, "FirestoreDailyBriefDeliveryRepository", lambda *_args, **_kwargs: InMemoryDailyBriefDeliveryRepository())
    monkeypatch.setattr(scheduled_daily_brief, "FirestoreDailyBriefRepository", lambda *_args, **_kwargs: InMemoryDailyBriefRepository())
    monkeypatch.setattr(scheduled_daily_brief, "FirestoreContextRepository", lambda *_args, **_kwargs: FakeContextRepository())
    monkeypatch.setenv("DAILY_BRIEF_SCHEDULE_ENABLED", "true")
    monkeypatch.setenv("DAILY_BRIEF_SCHEDULE_RECIPIENTS", "user@example.com")
    monkeypatch.setenv("DAILY_BRIEF_DELIVERY_RECIPIENTS", "user@example.com")

    assert scheduled_daily_brief.main_with_args(["--dry-run", "--json", "--timezone", "UTC", "--date", "2026-07-15", "--trigger", "test"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run"]["status"] == "skipped"
    assert "user@example.com" not in json.dumps(payload)


def test_doctor_scheduled_config_checks(monkeypatch, capsys):
    summary = doctor.CheckSummary()
    monkeypatch.setenv("DAILY_BRIEF_SCHEDULE_ENABLED", "true")
    monkeypatch.setenv("DAILY_BRIEF_SCHEDULE_MODE", "send")
    monkeypatch.setenv("DAILY_BRIEF_SCHEDULE_RECIPIENTS", "user@example.com")
    monkeypatch.setenv("DAILY_BRIEF_DELIVERY_RECIPIENTS", "other@example.com")
    monkeypatch.delenv("DAILY_BRIEF_DELIVERY_ALLOW_SEND", raising=False)

    doctor.check_scheduled_daily_brief_config(summary)

    output = capsys.readouterr().out
    assert "us***@example.com" in output
    assert "user@example.com" not in output
    assert summary.error >= 2


def test_smoke_scheduled_daily_brief_rejects_send(monkeypatch, capsys):
    payload = {"run": {"delivery_mode": "send", "status": "skipped", "idempotency_key": "key"}}
    monkeypatch.setattr(smoke, "run", lambda _cmd: completed(json.dumps(payload), 0))

    assert smoke.smoke_scheduled_daily_brief("project") == 1


def test_double_check_cli_scheduled(monkeypatch, capsys):
    class FakeRepo:
        def __init__(self, *_args, **_kwargs):
            pass

        def list_recent(self, limit=50):
            return [sample_run(status="running", started_at="2026-07-15T00:00:00+00:00")]

    monkeypatch.setattr(double_check, "FirestoreScheduledBriefRepository", FakeRepo)

    assert double_check.main_with_args(["--scheduled-daily-brief", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scheduled_daily_brief"] is True
    assert payload["read_only"] is True


def make_service(context_engine=None, client=None, run_repository=None):
    return ScheduledDailyBriefService(
        context_engine=context_engine or FakeContextEngine(),
        brief_builder=__import__("app.daily_brief", fromlist=["DailyBriefBuilder"]).DailyBriefBuilder(),
        brief_repository=InMemoryDailyBriefRepository(),
        delivery_service=DailyBriefDeliveryService(
            repository=InMemoryDailyBriefDeliveryRepository(),
            client=client,
        ),
        run_repository=run_repository or InMemoryScheduledBriefRepository(),
    )


def delivery_settings(**overrides):
    from app.config import DailyBriefDeliverySettings

    data = {
        "enabled": True,
        "mode": "draft",
        "recipients": ("user@example.com",),
        "allow_send": False,
        "start_hour": 0,
        "end_hour": 24,
        "timezone": "UTC",
    }
    data.update(overrides)
    return DailyBriefDeliverySettings(**data)


def sample_run(**overrides):
    data = {
        "run_id": "run",
        "schedule_date": "2026-07-15",
        "timezone": "UTC",
        "account_scope": "all",
        "delivery_mode": "draft",
        "recipient_hash": "recipient:hash",
        "idempotency_key": "key",
        "status": "pending",
        "started_at": "2026-07-15T07:30:00+00:00",
    }
    data.update(overrides)
    return ScheduledDailyBriefRun(**data)


class FakeContextEngine:
    def build_snapshot(self, *, account_ids=None, now=None, limit=100):
        return ContextSnapshot.empty(date="2026-07-15")


class FakeContextRepository:
    def load_context_data(self, *, account_ids=None, limit=100):
        from app.context.store import ContextData

        return ContextData()


def completed(stdout: str, returncode: int):
    import subprocess

    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")
