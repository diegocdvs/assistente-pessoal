from __future__ import annotations

import json

from scripts import double_check


class FakeRepository:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def load_context_data(self, *, account_ids=None, limit=100):
        from app.context.store import ContextData

        return ContextData(
            emails=[
                {
                    "id": "msg-1",
                    "account_id": "pessoal",
                    "provider": "gmail",
                    "sender": "News <news@example.com>",
                    "raw_headers": {"List-Unsubscribe": "<https://example.com/u>"},
                }
            ],
            subscriptions=[],
        )


class FakeContextEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def build_snapshot(self, *, account_ids=None):
        class Snapshot:
            def to_dict(self):
                return {"subscriptions_total": 0}

        return Snapshot()


def test_double_check_cli_is_read_only_and_reports_json(monkeypatch, capsys):
    monkeypatch.setattr(double_check, "FirestoreContextRepository", FakeRepository)
    monkeypatch.setattr(double_check, "ContextEngine", FakeContextEngine)

    assert double_check.main_with_args(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["read_only"] is True
    assert payload["status"] == "warning"
    assert payload["discrepancies_count"] == 1
