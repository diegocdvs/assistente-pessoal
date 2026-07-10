from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.context.models import ContextSnapshot
from app.daily_brief import (
    DailyBriefBuilder,
    DailyBriefDoubleCheck,
    DailyBriefJsonRenderer,
    DailyBriefSection,
    DailyBriefTextRenderer,
    FirestoreDailyBriefRepository,
    InMemoryDailyBriefRepository,
)
from scripts import daily_brief


def test_daily_brief_empty_ok_and_serialization():
    brief = DailyBriefBuilder().build(ContextSnapshot.empty(date="2026-07-10"))

    assert brief.status == "OK"
    assert brief.summary_metrics["meetings_today"] == 0
    assert brief.to_dict()["sections"][0]["key"] == "agenda"


def test_daily_brief_warning_for_conflict_and_critical_email():
    snapshot = ContextSnapshot.empty(date="2026-07-10")
    snapshot = replace_snapshot(
        snapshot,
        calendar_conflicts=[{"type": "overlap"}],
        emails_critical=[{"id": "email-1"}],
    )

    brief = DailyBriefBuilder().build(snapshot)

    assert brief.status == "WARNING"
    assert "Atencao" in brief.headline
    assert brief.summary_metrics["conflicts_count"] == 1


def test_daily_brief_error_for_critical_audit():
    brief = DailyBriefBuilder().build(
        ContextSnapshot.empty(date="2026-07-10"),
        audit_status="ERROR",
        open_discrepancies=[{"severity": "critical"}],
    )

    assert brief.status == "ERROR"


def test_daily_brief_section_validation():
    section = DailyBriefSection("agenda", "Agenda", 1, "OK", [], "sem itens", 0)

    assert section.to_dict()["schema_version"]


def test_text_and_json_renderers_are_stable():
    snapshot = replace_snapshot(
        ContextSnapshot.empty(date="2026-07-10"),
        calendar_events_today=[{"id": "event", "title": "Reuniao", "start_at": "2026-07-10T10:00:00+00:00"}],
    )
    brief = DailyBriefBuilder().build(snapshot, timezone_name="UTC")

    text = DailyBriefTextRenderer().render(brief)
    payload = json.loads(DailyBriefJsonRenderer().render(brief))

    assert "DAILY BRIEF" in text
    assert payload["schema_version"]


def test_repository_idempotency_and_latest():
    repo = InMemoryDailyBriefRepository()
    brief = DailyBriefBuilder().build(ContextSnapshot.empty(date="2026-07-10"))

    assert repo.save(brief) == "2026-07-10:all"
    repo.save(brief)

    assert repo.latest().brief_id == brief.brief_id


def test_firestore_repository_uses_daily_briefs_collection():
    client = Mock()
    brief = DailyBriefBuilder().build(ContextSnapshot.empty(date="2026-07-10"))
    with patch("app.daily_brief.repository.firestore.Client", return_value=client):
        FirestoreDailyBriefRepository("project").save(brief)

    client.collection.assert_called_with("daily_briefs")


def test_daily_brief_double_check():
    brief = DailyBriefBuilder().build(
        replace_snapshot(ContextSnapshot.empty(date="2026-07-10"), high_risk_items=[{"id": "risk"}])
    ).to_dict()
    brief["status"] = "OK"

    discrepancies = DailyBriefDoubleCheck().inspect(brief)

    assert any(item.type == "daily_brief_status_incompatible_with_risk" for item in discrepancies)


def test_daily_brief_cli_help_modes():
    with pytest.raises(SystemExit) as exc:
        daily_brief.main_with_args(["--help"])
    assert exc.value.code == 0


def test_daily_brief_cli_with_fake_context(monkeypatch, capsys):
    class FakeContextRepository:
        def __init__(self, *_args, **_kwargs):
            pass

        def load_context_data(self, *, account_ids=None, limit=100):
            from app.context.store import ContextData

            return ContextData()

    class FakeBriefRepository:
        def __init__(self, *_args, **_kwargs):
            pass

        def save(self, brief):
            return brief.date

        def latest(self):
            return None

    monkeypatch.setattr(daily_brief, "FirestoreContextRepository", FakeContextRepository)
    monkeypatch.setattr(daily_brief, "FirestoreDailyBriefRepository", FakeBriefRepository)

    assert daily_brief.main_with_args(["--json", "--no-persist"]) == 0
    assert '"brief_id"' in capsys.readouterr().out


def replace_snapshot(snapshot: ContextSnapshot, **changes):
    data = snapshot.to_dict()
    data.update(changes)
    data["followups"] = []
    data["top_priorities"] = []
    data["subscription_candidates"] = []
    from app.context.models import OperationalSummary

    summary = data["summary"]
    data["summary"] = OperationalSummary(
        total_emails=summary["total_emails"],
        critical_emails=summary["critical_emails"],
        followups=summary["followups"],
        pending_action_plans=summary["pending_action_plans"],
        subscriptions_detected=summary["subscriptions_detected"],
        subscriptions_recommended_for_unsubscribe=summary["subscriptions_recommended_for_unsubscribe"],
        top_category=summary["top_category"],
        top_priority=summary["top_priority"],
        total_by_category=summary["total_by_category"],
        total_by_priority=summary["total_by_priority"],
    )
    return ContextSnapshot(**{key: value for key, value in data.items() if key != "schema_version"})
