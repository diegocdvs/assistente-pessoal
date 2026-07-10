from __future__ import annotations

import json

from app.communication.models import SubscriptionEntity
from scripts import subscriptions


class FakeRepository:
    def __init__(self, *_args, **_kwargs) -> None:
        self.items = [make_subscription()]

    def list_subscriptions(self, *, account_id=None, status=None):
        values = self.items
        if account_id:
            values = [item for item in values if item.account_id == account_id]
        if status:
            values = [item for item in values if item.status == status]
        return values

    def get_subscription(self, account_id, subscription_id):
        return self.items[0]

    def upsert_subscription(self, subscription):
        self.items = [subscription]
        return subscription

    def save_approval(self, approval, *, account_id):
        return approval.approval_id


class FakeContextRepository:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def load_context_data(self, *, account_ids=None, limit=100):
        from app.context.store import ContextData

        return ContextData(
            emails=[
                {
                    "id": "msg-1",
                    "provider": "gmail",
                    "account_id": "pessoal",
                    "sender": "News <news@example.com>",
                    "received_at": "2026-07-10T10:00:00+00:00",
                    "raw_headers": {
                        "List-ID": "News <news.example.com>",
                        "List-Unsubscribe": "<https://example.com/u>",
                    },
                }
            ],
            classifications={"msg-1": {"category": "newsletter"}},
        )


def test_cli_json_redacts_sensitive_targets(monkeypatch, capsys):
    monkeypatch.setattr(subscriptions, "FirestoreSubscriptionRepository", FakeRepository)

    assert subscriptions.main_with_args(["--json"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["dry_run"] is True
    assert output["unsubscribe_execution_available"] is False
    assert "unsubscribe_url" not in output["subscriptions"][0]
    assert output["subscriptions"][0]["unsubscribe_methods"][0]["target"] == "https://example.com/[redacted]"


def test_cli_summary(monkeypatch, capsys):
    monkeypatch.setattr(subscriptions, "FirestoreSubscriptionRepository", FakeRepository)

    assert subscriptions.main_with_args(["--summary"]) == 0

    output = capsys.readouterr().out
    assert "subscriptions_total=1" in output
    assert "unsubscribe_execution_available=false" in output


def test_cli_detect_persisted_uses_context_repository(monkeypatch, capsys):
    monkeypatch.setattr(subscriptions, "FirestoreSubscriptionRepository", FakeRepository)
    monkeypatch.setattr(subscriptions, "FirestoreContextRepository", FakeContextRepository)

    assert subscriptions.main_with_args(["--detect-persisted", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["summary"]["subscriptions_total"] == 1


def make_subscription() -> SubscriptionEntity:
    return SubscriptionEntity(
        subscription_id="subscription:test",
        account_id="pessoal",
        provider="gmail",
        sender="news@example.com",
        sender_domain="example.com",
        display_name="News",
        list_id="news.example.com",
        category="newsletter",
        first_seen_at="2026-07-01T10:00:00+00:00",
        last_received_at="2026-07-10T10:00:00+00:00",
        message_count=10,
        estimated_frequency="daily",
        unsubscribe_supported=True,
        unsubscribe_methods=[
            {
                "method": "https",
                "target": "https://example.com/u?token=secret",
                "redacted_target": "https://example.com/[redacted]",
                "one_click": True,
            }
        ],
        unsubscribe_url="https://example.com/u?token=secret",
        one_click_supported=True,
        status="unsubscribe_recommended",
        recommendation_score=90,
    )
