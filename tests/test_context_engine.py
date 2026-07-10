from __future__ import annotations

from datetime import datetime, timezone

from app.context import ContextEngine, ContextSnapshot, FollowUpDetector, InMemoryContextRepository, PriorityRanker


NOW = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def make_email(
    message_id: str,
    *,
    account_id: str = "pessoal",
    provider: str = "gmail",
    subject: str = "Assunto",
    sender: str = "Pessoa <pessoa@example.com>",
    received_at: str = "2026-07-09T10:00:00+00:00",
    labels: list[str] | None = None,
    thread_id: str = "thread-1",
) -> dict:
    return {
        "id": message_id,
        "provider": provider,
        "account_id": account_id,
        "account_email": f"{account_id}@example.com",
        "thread_id": thread_id,
        "subject": subject,
        "sender": sender,
        "recipients": [f"{account_id}@example.com"],
        "snippet": "Resumo",
        "labels": labels or ["INBOX"],
        "received_at": received_at,
        "raw_headers": {},
        "metadata": {},
    }


def test_context_snapshot_serializes_operational_state():
    snapshot = ContextSnapshot.empty(date="2026-07-09")

    payload = snapshot.to_dict()

    assert payload["schema_version"] == "0.2"
    assert payload["date"] == "2026-07-09"
    assert payload["summary"]["total_emails"] == 0
    assert payload["top_priorities"] == []


def test_priority_ranker_scores_by_priority_category_action_age_and_followup():
    work_item = {
        "id": "gmail:msg-1",
        "source": "gmail",
        "type": "email",
        "account_id": "pessoal",
        "created_at": "2026-07-01T10:00:00+00:00",
        "payload": {"id": "msg-1", "received_at": "2026-07-01T10:00:00+00:00"},
    }

    ranked = PriorityRanker().rank(
        [work_item],
        {"msg-1": {"category": "financeiro", "priority": "critica"}},
        {"msg-1": [{"type": "review_financial", "status": "planned"}]},
        followup_ids={"msg-1"},
        now=NOW,
    )

    assert ranked[0].score == 197
    assert ranked[0].reasons == [
        "priority:critica",
        "category:financeiro",
        "old_pending",
        "action:review_financial:planned",
        "followup",
    ]


def test_followup_detector_finds_sent_without_reply_old_pending_and_forgotten_items():
    emails = [
        make_email(
            "sent-1",
            labels=["SENT"],
            thread_id="thread-sent",
            received_at="2026-07-01T10:00:00+00:00",
        ),
        make_email(
            "old-1",
            subject="Fatura antiga",
            thread_id="thread-old",
            received_at="2026-07-01T10:00:00+00:00",
        ),
    ]
    work_items = [
        {
            "id": "gmail:forgotten-1",
            "source": "gmail",
            "type": "email",
            "account_id": "pessoal",
            "created_at": "2026-07-01T10:00:00+00:00",
            "payload": {"id": "forgotten-1", "received_at": "2026-07-01T10:00:00+00:00"},
        }
    ]

    suggestions = FollowUpDetector().detect(
        emails,
        work_items,
        {"old-1": {"category": "financeiro", "priority": "alta"}},
        {"old-1": [{"type": "review_financial", "status": "planned"}]},
        now=NOW,
    )

    assert [suggestion.type for suggestion in suggestions] == [
        "sent_without_reply",
        "old_pending",
        "forgotten_work_item",
    ]
    assert all(suggestion.age_days == 8 for suggestion in suggestions)


def test_context_engine_builds_summary_priorities_and_context_api():
    emails = [
        make_email("critical-1", subject="Novo login", sender="Security <sec@example.com>"),
        make_email(
            "event-1",
            subject="Reuniao amanha",
            sender="Cliente <cliente@example.com>",
            received_at="2026-07-08T10:00:00+00:00",
        ),
        make_email(
            "noise-1",
            subject="Cupom",
            sender="Promo <promo@example.com>",
            received_at="2026-07-08T10:00:00+00:00",
        ),
    ]
    repository = InMemoryContextRepository(
        emails=emails,
        classifications={
            "critical-1": {
                "category": "seguranca",
                "priority": "critica",
                "reason": "Aviso de seguranca.",
                "possible_event": False,
            },
            "event-1": {
                "category": "evento",
                "priority": "alta",
                "reason": "Possivel compromisso.",
                "possible_event": True,
            },
            "noise-1": {
                "category": "promocao",
                "priority": "ruido",
                "reason": "Promocao.",
                "possible_event": False,
            },
        },
        action_plans={
            "critical-1": [{"type": "highlight_critical", "status": "planned", "reason": "Destacar."}],
            "event-1": [{"type": "review_event_candidate", "status": "planned", "reason": "Revisar."}],
        },
        reports=[
            {
                "run_id": "run-1",
                "planned_actions": [
                    {
                        "type": "highlight_critical",
                        "status": "planned",
                        "reason": "Destacar.",
                        "email_id": "critical-1",
                        "account_id": "pessoal",
                    }
                ],
            }
        ],
    )

    snapshot = ContextEngine(repository).build_snapshot(now=NOW)

    assert snapshot.date == "2026-07-09"
    assert snapshot.summary.total_emails == 3
    assert snapshot.summary.critical_emails == 1
    assert snapshot.summary.pending_action_plans == 2
    assert snapshot.summary.top_priority == "critica"
    assert snapshot.summary.total_by_category == {"seguranca": 1, "evento": 1, "promocao": 1}
    assert [email["id"] for email in snapshot.emails_pending] == ["critical-1", "event-1"]
    assert [email["id"] for email in snapshot.emails_critical] == ["critical-1"]
    assert snapshot.upcoming_commitments[0]["email_id"] == "event-1"
    assert snapshot.important_people == ["sec@example.com", "cliente@example.com", "promo@example.com"]
    assert snapshot.recent_decisions[0]["run_id"] == "run-1"
    assert snapshot.source_counts == {"gmail": 3}
    assert snapshot.top_priorities[0].work_item["payload"]["id"] == "critical-1"


def test_in_memory_context_repository_filters_by_account():
    repository = InMemoryContextRepository(
        emails=[
            make_email("msg-1", account_id="pessoal"),
            make_email("msg-2", account_id="trabalho"),
        ],
        classifications={
            "msg-1": {"priority": "alta"},
            "msg-2": {"priority": "normal"},
        },
        action_plans={
            "msg-1": [{"status": "planned"}],
            "msg-2": [{"status": "planned"}],
        },
        reports=[
            {"accounts": [{"id": "pessoal"}], "run_id": "run-1"},
            {"accounts": [{"id": "trabalho"}], "run_id": "run-2"},
        ],
    )

    data = repository.load_context_data(account_ids=["pessoal"])

    assert [email["id"] for email in data.emails] == ["msg-1"]
    assert data.classifications == {"msg-1": {"priority": "alta"}}
    assert data.action_plans == {"msg-1": [{"status": "planned"}]}
    assert [report["run_id"] for report in data.reports] == ["run-1"]
