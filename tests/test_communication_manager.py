from __future__ import annotations

from unittest.mock import Mock, patch

from app.communication import (
    CommunicationManager,
    InMemorySubscriptionRepository,
    SubscriptionAggregator,
    SubscriptionApproval,
    SubscriptionDoubleCheck,
    SubscriptionRecommendationEngine,
)
from app.communication.models import SubscriptionEntity, SubscriptionStatus
from app.communication.repository import FirestoreSubscriptionRepository
from app.communication.rfc_parser import parse_unsubscribe_methods
from app.communication.subscriptions import SubscriptionDetector
from app.context import ContextEngine, InMemoryContextRepository
from app.security.models import RiskLevel, SecurityAssessment


def make_email(message_id: str = "msg-1", headers: dict[str, str] | None = None, sender: str = "News <news@example.com>") -> dict:
    return {
        "id": message_id,
        "provider": "gmail",
        "account_id": "pessoal",
        "account_email": "user@example.com",
        "thread_id": "thread-1",
        "subject": "Newsletter",
        "sender": sender,
        "recipients": ["user@example.com"],
        "snippet": "Resumo sem links",
        "labels": ["INBOX"],
        "received_at": "2026-07-10T10:00:00+00:00",
        "raw_headers": headers or {},
        "metadata": {},
    }


def test_rfc_parser_multiple_methods_one_click_and_dedupes():
    methods = parse_unsubscribe_methods(
        {
            "List-Unsubscribe": "<mailto:leave@example.com>, <https://example.com/u?id=123>, <https://example.com/u?id=123>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    )

    assert [method.method for method in methods] == ["mailto", "https"]
    assert methods[1].one_click is True
    assert methods[1].redacted_target == "https://example.com/[redacted]"
    assert methods[0].redacted_target == "l***@example.com"


def test_rfc_parser_ignores_malformed_and_absent_headers():
    assert parse_unsubscribe_methods({"List-Unsubscribe": "<not a url>"}) == []
    assert parse_unsubscribe_methods({}) == []


def test_detector_prioritizes_rfc_headers_not_subject_guessing():
    detector = SubscriptionDetector()
    detected = detector.detect_email(
        make_email(
            headers={
                "List-ID": "Example <news.example.com>",
                "List-Post": "<mailto:post@example.com>",
                "Precedence": "bulk",
            }
        )
    )

    assert detected.detected is True
    assert detected.list_id == "news.example.com"
    assert "header:list-id" in detected.reasons
    assert detector.detect_email(make_email(headers={}, sender="Promo <promo@example.com>")).detected is False


def test_aggregator_groups_by_list_id_and_is_deterministic():
    emails = [
        make_email("msg-1", {"List-ID": "Example <news.example.com>", "List-Unsubscribe": "<https://example.com/a>"}),
        make_email("msg-2", {"List-ID": "Example <news.example.com>", "List-Unsubscribe": "<https://example.com/a>"}),
    ]

    subscriptions = SubscriptionAggregator().aggregate(emails, classifications={"msg-1": {"category": "newsletter"}})

    assert len(subscriptions) == 1
    assert subscriptions[0].message_count == 2
    assert subscriptions[0].estimated_frequency in {"daily", "weekly", "monthly", "rare"}
    assert subscriptions[0].list_id == "news.example.com"


def test_aggregator_falls_back_to_sender_identity():
    emails = [
        make_email("msg-1", {"Precedence": "list"}, "Digest <digest@example.com>"),
        make_email("msg-2", {"Precedence": "list"}, "Digest <digest@example.com>"),
    ]

    subscriptions = SubscriptionAggregator().aggregate(emails)

    assert len(subscriptions) == 1
    assert subscriptions[0].sender == "digest@example.com"


def test_in_memory_repository_upsert_and_status_filters():
    repo = InMemorySubscriptionRepository()
    subscription = make_subscription(status="detected")

    repo.upsert_subscription(subscription)
    repo.upsert_subscription(subscription)

    assert repo.get_subscription("pessoal", subscription.subscription_id) is not None
    assert repo.list_subscriptions(status="detected")[0].message_count == 12


def test_firestore_repository_upsert_uses_expected_path():
    client = Mock()
    subscription = make_subscription()
    with patch("app.communication.repository.firestore.Client", return_value=client):
        repo = FirestoreSubscriptionRepository(project_id="project")
        repo.upsert_subscription(subscription)

    client.collection.assert_called_with("accounts")
    client.collection.return_value.document.assert_called_with("pessoal")


def test_recommendation_engine_respects_favorite_ignored_and_missing_mechanism():
    engine = SubscriptionRecommendationEngine()

    assert engine.evaluate(make_subscription(status="favorite")).recommended is False
    assert engine.evaluate(make_subscription(status="ignored")).recommended is False
    assert engine.evaluate(make_subscription(unsubscribe_supported=False, methods=[])).recommended is False


def test_high_risk_blocks_recommendation_but_plan_is_not_executable():
    manager = CommunicationManager()
    subscription = make_subscription(risk_level="high", risk_score=90)
    recommendation = SubscriptionRecommendationEngine().evaluate(subscription)

    plan = manager.plan_unsubscribe(subscription, recommendation)

    assert recommendation.blocked_by_security is True
    assert plan is not None
    assert plan.status == "waiting_approval"
    assert plan.payload["approval_required"] is True
    assert plan.payload["execution_enabled"] is False
    assert plan.payload["dry_run"] is True


def test_manager_processes_subscriptions_and_creates_waiting_approval_plan():
    email = make_email(
        headers={
            "List-ID": "Example <news.example.com>",
            "List-Unsubscribe": "<https://example.com/u>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    )
    manager = CommunicationManager(repository=InMemorySubscriptionRepository())

    result = manager.process_emails(
        [email],
        classifications={"msg-1": {"category": "newsletter"}},
    )

    assert result["subscriptions"][0].status == SubscriptionStatus.UNSUBSCRIBE_RECOMMENDED.value
    assert result["action_plans"][0].type == "unsubscribe_subscription"
    assert result["action_plans"][0].payload["target"] == "https://example.com/[redacted]"


def test_approval_model_is_serializable_without_execution():
    approval = SubscriptionApproval(subscription_id="sub-1", action_plan_id="plan-1", status="pending")

    assert approval.to_dict()["status"] == "pending"
    assert approval.to_dict()["schema_version"]


def test_context_snapshot_includes_subscription_counts_from_repository_data():
    subscription = make_subscription(status="unsubscribe_recommended").to_dict()
    repository = InMemoryContextRepository(
        emails=[make_email()],
        classifications={"msg-1": {"category": "newsletter", "priority": "baixa"}},
        subscriptions=[subscription],
    )

    snapshot = ContextEngine(repository).build_snapshot()

    assert snapshot.subscriptions_total == 1
    assert snapshot.subscriptions_recommended_for_unsubscribe == 1
    assert "Foram identificadas 1 inscricoes." in snapshot.summary.subscription_summary_lines
    assert "unsubscribe_url" not in snapshot.top_subscription_candidates[0]


def test_double_check_reports_subscription_discrepancies_read_only():
    checker = SubscriptionDoubleCheck()
    discrepancies = checker.inspect(
        emails=[make_email(headers={"List-Unsubscribe": "<https://example.com/u>"})],
        subscriptions=[],
        action_plans=[
            {
                "type": "unsubscribe_subscription",
                "payload": {
                    "subscription_id": "missing",
                    "approval_required": False,
                    "execution_enabled": True,
                },
            }
        ],
        context_snapshot={"subscriptions_total": 1},
    )

    types = {item.type for item in discrepancies}
    assert "subscription_headers_without_entity" in types
    assert "action_plan_without_subscription" in types
    assert "action_plan_without_required_approval" in types
    assert "action_plan_execution_enabled" in types
    assert "context_subscription_count_mismatch" in types


def test_no_http_request_or_email_send_is_performed(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("external side effect attempted")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    manager = CommunicationManager(repository=InMemorySubscriptionRepository())
    result = manager.process_emails(
        [
            make_email(
                headers={
                    "List-ID": "Example <news.example.com>",
                    "List-Unsubscribe": "<mailto:leave@example.com>, <https://example.com/u>",
                }
            )
        ],
        classifications={"msg-1": {"category": "newsletter"}},
    )

    assert result["action_plans"][0].payload["execution_enabled"] is False


def make_subscription(
    *,
    status: str = "detected",
    unsubscribe_supported: bool = True,
    methods: list[dict] | None = None,
    risk_level: str | None = None,
    risk_score: int | None = None,
) -> SubscriptionEntity:
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
        message_count=12,
        estimated_frequency="daily",
        unsubscribe_supported=unsubscribe_supported,
        unsubscribe_methods=methods
        if methods is not None
        else [{"method": "https", "target": "https://example.com/u", "redacted_target": "https://example.com/[redacted]"}],
        unsubscribe_url="https://example.com/u" if unsubscribe_supported else None,
        one_click_supported=True,
        status=status,
        latest_security_risk_level=risk_level,
        latest_security_risk_score=risk_score,
    )


def make_security_assessment(level: RiskLevel = RiskLevel.HIGH) -> SecurityAssessment:
    return SecurityAssessment(
        assessment_id="assessment",
        provider="gmail",
        source_id="msg-1",
        risk_score=90,
        risk_level=level,
        risk_reasons=["test"],
        link_count=0,
        attachment_count=0,
        external_images=0,
        suspicious_headers=[],
        spoofing_signals=[],
        authentication_signals=[],
    )
