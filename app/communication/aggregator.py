from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any

from app.communication.models import SubscriptionEntity
from app.communication.rfc_parser import preferred_unsubscribe_method
from app.communication.subscriptions import SubscriptionDetector
from app.core.models import Category, EmailEntity, SCHEMA_VERSION
from app.security.models import SecurityAssessment


class SubscriptionAggregator:
    def __init__(self, detector: SubscriptionDetector | None = None) -> None:
        self.detector = detector or SubscriptionDetector()

    def aggregate(
        self,
        emails: list[EmailEntity | dict[str, Any]],
        *,
        classifications: dict[str, dict[str, Any]] | None = None,
        security_assessments: dict[str, SecurityAssessment] | None = None,
        existing: list[SubscriptionEntity] | None = None,
    ) -> list[SubscriptionEntity]:
        by_identity = {_identity_from_subscription(subscription): subscription for subscription in existing or []}
        classifications = classifications or {}
        security_assessments = security_assessments or {}

        for email_value in emails:
            email = _email_dict(email_value)
            result = self.detector.detect_email(email)
            if not result.detected:
                continue
            identity = _identity_from_email(email, result.list_id, result.parsed_methods)
            current = by_identity.get(identity)
            by_identity[identity] = self._merge(
                current,
                email=email,
                detection=result,
                category=classifications.get(str(email.get("id")), {}).get("category"),
                security=security_assessments.get(str(email.get("id"))),
            )

        return sorted(by_identity.values(), key=lambda item: item.subscription_id)

    def _merge(
        self,
        current: SubscriptionEntity | None,
        *,
        email: dict[str, Any],
        detection: Any,
        category: str | None,
        security: SecurityAssessment | None,
    ) -> SubscriptionEntity:
        now = datetime.now(timezone.utc).isoformat()
        sender_name, sender_address = parseaddr(str(email.get("sender") or ""))
        sender = sender_address or str(email.get("sender") or "")
        sender_domain = sender.split("@", 1)[1].lower() if "@" in sender else None
        received_at = str(email.get("received_at") or email.get("last_seen_at") or now)
        preferred = preferred_unsubscribe_method(detection.parsed_methods)
        methods = [method.to_dict() for method in detection.parsed_methods]
        subscription_id = _subscription_id(email, detection.list_id, preferred.target if preferred else None, sender)
        audit_metadata = {
            "latest_email_id": email.get("id"),
            "latest_detection": detection.to_dict(),
            "identity_strategy": _identity_strategy(email, detection.list_id, preferred.target if preferred else None),
        }

        if current is None:
            return SubscriptionEntity(
                subscription_id=subscription_id,
                account_id=str(email.get("account_id") or ""),
                provider=str(email.get("provider") or "unknown"),
                sender=sender,
                sender_domain=sender_domain,
                display_name=sender_name or None,
                list_id=detection.list_id,
                category=category or Category.OUTROS.value,
                first_seen_at=received_at,
                last_received_at=received_at,
                message_count=1,
                estimated_frequency="unknown",
                unsubscribe_supported=bool(preferred),
                unsubscribe_methods=methods,
                unsubscribe_url=preferred.target if preferred and preferred.method in {"http", "https"} else None,
                unsubscribe_email=preferred.target if preferred and preferred.method == "mailto" else None,
                one_click_supported=any(method.one_click for method in detection.parsed_methods),
                latest_security_risk_level=security.risk_level.value if security else None,
                latest_security_risk_score=security.risk_score if security else None,
                audit_metadata=audit_metadata,
                schema_version=SCHEMA_VERSION,
            )

        first_seen = min(str(current.first_seen_at), received_at)
        last_received = max(str(current.last_received_at), received_at)
        merged_methods = _merge_methods(current.unsubscribe_methods, methods)
        return replace(
            current,
            sender=sender or current.sender,
            sender_domain=sender_domain or current.sender_domain,
            display_name=sender_name or current.display_name,
            list_id=detection.list_id or current.list_id,
            category=category or current.category,
            first_seen_at=first_seen,
            last_received_at=last_received,
            message_count=current.message_count + 1,
            estimated_frequency=_estimate_frequency(first_seen, last_received, current.message_count + 1),
            unsubscribe_supported=bool(merged_methods),
            unsubscribe_methods=merged_methods,
            unsubscribe_url=current.unsubscribe_url or (
                preferred.target if preferred and preferred.method in {"http", "https"} else None
            ),
            unsubscribe_email=current.unsubscribe_email or (
                preferred.target if preferred and preferred.method == "mailto" else None
            ),
            one_click_supported=current.one_click_supported or any(method.one_click for method in detection.parsed_methods),
            latest_security_risk_level=security.risk_level.value if security else current.latest_security_risk_level,
            latest_security_risk_score=security.risk_score if security else current.latest_security_risk_score,
            updated_at=now,
            audit_metadata={**current.audit_metadata, **audit_metadata},
        )


def _email_dict(email: EmailEntity | dict[str, Any]) -> dict[str, Any]:
    return email.to_dict() if isinstance(email, EmailEntity) else dict(email)


def _identity_from_email(email: dict[str, Any], list_id: str | None, methods: list[Any]) -> str:
    preferred = preferred_unsubscribe_method(methods)
    return _identity(email.get("account_id"), email.get("provider"), list_id, _sender_domain(email), preferred.target if preferred else None, email.get("sender"))


def _identity_from_subscription(subscription: SubscriptionEntity) -> str:
    target = subscription.unsubscribe_url or subscription.unsubscribe_email
    return _identity(subscription.account_id, subscription.provider, subscription.list_id, subscription.sender_domain, target, subscription.sender)


def _identity(account_id: Any, provider: Any, list_id: str | None, sender_domain: str | None, target: str | None, sender: Any) -> str:
    base = f"{account_id}:{provider}:"
    if list_id:
        return base + f"list:{list_id.lower()}"
    if sender_domain and target:
        return base + f"domain-target:{sender_domain.lower()}:{target.lower()}"
    return base + f"sender:{str(sender or '').lower()}"


def _identity_strategy(email: dict[str, Any], list_id: str | None, target: str | None) -> str:
    if list_id:
        return "list_id"
    if _sender_domain(email) and target:
        return "sender_domain_unsubscribe_target"
    return "sender"


def _subscription_id(email: dict[str, Any], list_id: str | None, target: str | None, sender: str) -> str:
    identity = _identity(email.get("account_id"), email.get("provider"), list_id, _sender_domain(email), target, sender)
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"subscription:{digest}"


def _sender_domain(email: dict[str, Any]) -> str | None:
    _name, sender_address = parseaddr(str(email.get("sender") or ""))
    sender = sender_address or str(email.get("sender") or "")
    return sender.split("@", 1)[1].lower() if "@" in sender else None


def _merge_methods(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for method in [*existing, *incoming]:
        key = (str(method.get("method")), str(method.get("target")).lower())
        merged[key] = method
    return list(merged.values())


def _estimate_frequency(first_seen: str, last_seen: str, count: int) -> str:
    if count <= 1:
        return "unknown"
    try:
        first = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
        last = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    days = max((last - first).days, 1)
    per_week = count / days * 7
    if per_week >= 7:
        return "daily"
    if per_week >= 2:
        return "weekly"
    if per_week >= 0.5:
        return "monthly"
    return "rare"
