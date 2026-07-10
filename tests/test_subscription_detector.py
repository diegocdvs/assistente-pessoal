from app.communication import SubscriptionDetector
from app.context import ContextEngine, InMemoryContextRepository


def make_email(message_id: str, raw_headers: dict[str, str]) -> dict:
    return {
        "id": message_id,
        "provider": "gmail",
        "account_id": "pessoal",
        "account_email": "user@example.com",
        "thread_id": message_id,
        "subject": "Newsletter",
        "sender": "Example News <news@example.com>",
        "recipients": ["user@example.com"],
        "snippet": "Resumo",
        "labels": ["INBOX"],
        "received_at": "2026-07-10T10:00:00+00:00",
        "raw_headers": raw_headers,
        "metadata": {},
    }


def test_subscription_detector_uses_rfc_headers_without_accessing_links():
    email = make_email(
        "msg-1",
        {
            "List-Unsubscribe": "<mailto:leave@example.com>, <https://example.com/unsubscribe/123>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "List-ID": "Example News <news.example.com>",
            "Precedence": "bulk",
        },
    )

    candidates = SubscriptionDetector().detect([email])

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.unsubscribe_supported is True
    assert candidate.unsubscribe_method == "http"
    assert candidate.unsubscribe_url == "https://example.com/unsubscribe/123"
    assert candidate.unsubscribe_email == "leave@example.com"
    assert candidate.sender_domain == "example.com"
    assert candidate.status == "detected"
    assert "list-unsubscribe" in candidate.evidence


def test_subscription_detector_does_not_guess_from_subject_only():
    email = make_email("msg-2", {})

    assert SubscriptionDetector().detect([email]) == []


def test_context_snapshot_exposes_subscription_counts_without_executing_unsubscribe():
    email = make_email(
        "msg-3",
        {"List-Unsubscribe": "<https://example.com/unsubscribe/3>", "List-ID": "Example"},
    )
    repository = InMemoryContextRepository(
        emails=[email],
        classifications={"msg-3": {"category": "newsletter", "priority": "baixa"}},
    )

    snapshot = ContextEngine(repository).build_snapshot()

    assert len(snapshot.subscription_candidates) == 1
    assert snapshot.summary.subscriptions_detected == 1
    assert snapshot.summary.subscriptions_recommended_for_unsubscribe == 1
    assert snapshot.action_plans == []
