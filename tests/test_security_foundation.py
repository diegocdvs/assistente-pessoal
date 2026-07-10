from __future__ import annotations

from app.context import ContextEngine, InMemoryContextRepository
from app.security import (
    AttachmentAnalyzer,
    DomainAnalyzer,
    HeaderAnalyzer,
    LinkAnalyzer,
    RiskEngine,
    RiskLevel,
    SecurityAuditor,
    SecurityDecision,
    SecurityEventFactory,
    SecurityEventType,
    SecurityPolicy,
    ThreatAnalyzer,
)


def make_email(**overrides):
    email = {
        "id": "msg-1",
        "provider": "gmail",
        "account_id": "pessoal",
        "account_email": "user@example.com",
        "thread_id": "thread-1",
        "subject": "Urgent account review",
        "sender": "PayPal <security@paypa1.com>",
        "recipients": ["user@example.com"],
        "snippet": "Open https://bit.ly/a?url=https://evil.test now <img src=\"https://track.test/pixel.png\">",
        "labels": ["INBOX"],
        "received_at": "2026-07-10T10:00:00+00:00",
        "raw_headers": {
            "From": "PayPal <security@paypa1.com>",
            "Reply-To": "Support <support@evil.test>",
            "Return-Path": "<bounce@evil.test>",
            "Authentication-Results": "mx.test; spf=fail smtp.mailfrom=evil.test; dkim=fail; dmarc=fail",
            "List-Unsubscribe": "<https://example.com/unsubscribe>",
            "List-ID": "Example List <example.test>",
            "X-Priority": "1",
        },
        "metadata": {
            "attachments": [
                {"filename": "invoice.pdf.exe", "mime_type": "application/x-msdownload", "size_bytes": 1234}
            ]
        },
    }
    email.update(overrides)
    return email


def test_domain_analyzer_detects_ip_punycode_unicode_tld_and_lookalike():
    analyzer = DomainAnalyzer()

    assert analyzer.analyze("192.168.0.1").is_ip_literal is True
    assert "punycode_domain" in analyzer.analyze("xn--pple-43d.com").risk_reasons
    assert "unicode_domain" in analyzer.analyze("exemploç.com").risk_reasons
    assert "uncommon_tld:zip" in analyzer.analyze("example.zip").risk_reasons
    assert analyzer.analyze("paypa1.com").looks_like == "paypal.com"
    assert analyzer.analyze("").is_empty is True


def test_link_analyzer_never_accesses_links_and_flags_static_risks():
    links = LinkAnalyzer().analyze_many("See https://bit.ly/a?url=https://evil.test and http://127.0.0.1:8080/x")

    assert len(links) == 2
    assert links[0].is_shortener is True
    assert "redirect_parameter" in links[0].risk_reasons
    assert links[1].is_ip_literal is True
    assert links[1].uncommon_port == 8080


def test_attachment_analyzer_flags_executable_and_double_extension():
    assessment = AttachmentAnalyzer().analyze(
        {"filename": "report.pdf.exe", "mime_type": "application/x-msdownload", "size_bytes": "42"}
    )

    assert assessment.suspicious is True
    assert assessment.has_double_extension is True
    assert assessment.is_executable is True
    assert assessment.size_bytes == 42


def test_header_analyzer_detects_subscription_auth_and_spoofing_signals():
    headers = HeaderAnalyzer().analyze(make_email()["raw_headers"])

    assert headers.list_unsubscribe is True
    assert headers.list_id is True
    assert headers.reply_to_differs is True
    assert "spf:fail" in headers.authentication_signals
    assert "spf:fail" in headers.spoofing_signals
    assert "reply_to_domain_differs" in headers.spoofing_signals
    assert "x_priority_high" in headers.suspicious_headers


def test_risk_engine_and_policy_are_deterministic():
    email = make_email()
    headers = HeaderAnalyzer().analyze(email["raw_headers"])
    links = LinkAnalyzer().analyze_many(email["snippet"])
    attachments = AttachmentAnalyzer().analyze_many(email["metadata"]["attachments"])

    score, level, reasons = RiskEngine().score(
        links=links,
        attachments=attachments,
        headers=headers,
        external_images=1,
    )

    assert score == 100
    assert level == RiskLevel.CRITICAL
    assert "attachment:executable_attachment" in reasons
    assert SecurityPolicy().decide(risk_score=score, risk_level=level) == SecurityDecision.QUARANTINE
    assert SecurityPolicy().decide(risk_score=80, risk_level=RiskLevel.HIGH) == SecurityDecision.BLOCK
    assert SecurityPolicy().decide(risk_score=65, risk_level=RiskLevel.HIGH) == SecurityDecision.REVIEW
    assert SecurityPolicy().decide(risk_score=35, risk_level=RiskLevel.MEDIUM) == SecurityDecision.WARN


def test_security_events_and_audit_record_are_serializable():
    email = make_email()
    headers = HeaderAnalyzer().analyze(email["raw_headers"])
    links = LinkAnalyzer().analyze_many(email["snippet"])
    attachments = AttachmentAnalyzer().analyze_many(email["metadata"]["attachments"])

    events = SecurityEventFactory().build(
        provider="gmail",
        source_id="msg-1",
        risk_level=RiskLevel.HIGH,
        links=links,
        attachments=attachments,
        headers=headers,
    )

    event_types = {event.type for event in events}
    assert SecurityEventType.HIGH_RISK_DETECTED in event_types
    assert SecurityEventType.SUSPICIOUS_ATTACHMENT in event_types
    assert SecurityEventType.SPOOFING_DETECTED in event_types
    assert SecurityEventType.SUBSCRIPTION_DETECTED in event_types
    assert SecurityEventType.LINK_WARNING in event_types

    assessment = ThreatAnalyzer().analyze(email)
    audit = SecurityAuditor().record(assessment)
    assert audit.assessment_id == assessment.assessment_id
    assert audit.to_dict()["decision"] == "quarantine"
    assert audit.to_dict()["schema_version"] == "0.2"


def test_threat_analyzer_builds_security_assessment_without_mutating_source():
    email = make_email()
    original = dict(email)

    assessment = ThreatAnalyzer().analyze(email)

    assert email == original
    assert assessment.provider == "gmail"
    assert assessment.source_id == "msg-1"
    assert assessment.risk_score == 100
    assert assessment.risk_level == RiskLevel.CRITICAL
    assert assessment.policy_decision == SecurityDecision.QUARANTINE
    assert assessment.link_count == 2
    assert assessment.attachment_count == 1
    assert assessment.external_images == 1
    assert assessment.suspicious_headers == ["x_priority_high"]
    assert "spf:fail" in assessment.authentication_signals
    assert assessment.to_dict()["schema_version"] == "0.2"


def test_context_snapshot_exposes_security_assessments_and_events():
    snapshot = ContextEngine(InMemoryContextRepository(emails=[make_email()])).build_snapshot()

    assert len(snapshot.high_risk_items) == 1
    assert snapshot.high_risk_items[0]["source_id"] == "msg-1"
    assert snapshot.warning_items == []
    assert {event["type"] for event in snapshot.security_events} >= {
        "HighRiskDetected",
        "SuspiciousAttachment",
        "SpoofingDetected",
        "SubscriptionDetected",
        "LinkWarning",
    }


def test_context_snapshot_exposes_warning_items_for_medium_risk():
    email = make_email(
        snippet="Visit https://bit.ly/a?url=https://evil.test and http://127.0.0.1:8080/x",
        raw_headers={},
        metadata={},
    )

    snapshot = ContextEngine(InMemoryContextRepository(emails=[email])).build_snapshot()

    assert snapshot.high_risk_items == []
    assert len(snapshot.warning_items) == 1
    assert snapshot.warning_items[0]["policy_decision"] == "warn"
