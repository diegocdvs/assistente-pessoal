from __future__ import annotations

from email.utils import parseaddr
from typing import Any

from app.communication.models import SubscriptionCandidate, SubscriptionDetectionResult
from app.communication.rfc_parser import (
    extract_list_id,
    normalize_headers,
    parse_unsubscribe_methods,
    preferred_unsubscribe_method,
    source_subscription_headers,
)


class SubscriptionDetector:
    """Detect subscription signals without accessing external URLs or mailto targets."""

    def detect(self, emails: list[dict[str, Any]]) -> list[SubscriptionCandidate]:
        candidates: list[SubscriptionCandidate] = []
        for email in emails:
            result = self.detect_email(email)
            if not result.detected:
                continue
            candidate = self._to_candidate(email, result)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def detect_email(self, email: dict[str, Any]) -> SubscriptionDetectionResult:
        headers = normalize_headers(email.get("raw_headers"))
        methods = parse_unsubscribe_methods(headers)
        list_id = extract_list_id(headers)
        precedence = headers.get("precedence", "").lower()
        auto_submitted = headers.get("auto-submitted", "").lower()
        list_post = headers.get("list-post", "")
        reasons: list[str] = []
        confidence = 0.0

        if headers.get("list-unsubscribe"):
            reasons.append("header:list-unsubscribe")
            confidence += 0.45
        if headers.get("list-unsubscribe-post"):
            reasons.append("header:list-unsubscribe-post")
            confidence += 0.15
        if list_id:
            reasons.append("header:list-id")
            confidence += 0.25
        if list_post:
            reasons.append("header:list-post")
            confidence += 0.10
        if precedence in {"bulk", "list", "junk"}:
            reasons.append(f"header:precedence:{precedence}")
            confidence += 0.10
        if auto_submitted and auto_submitted != "no":
            reasons.append("header:auto-submitted")
            confidence += 0.05

        detected = bool(headers.get("list-unsubscribe") or list_id or list_post or precedence in {"bulk", "list"})
        return SubscriptionDetectionResult(
            detected=detected,
            confidence=min(confidence, 1.0) if detected else 0.0,
            reasons=reasons,
            parsed_methods=methods,
            list_id=list_id,
            source_headers=source_subscription_headers(headers),
            risk_recommendation="official_mechanism_detected_review_required" if methods else "no_official_mechanism",
        )

    def _to_candidate(
        self,
        email: dict[str, Any],
        result: SubscriptionDetectionResult,
    ) -> SubscriptionCandidate | None:
        sender_name, sender_address = parseaddr(str(email.get("sender") or ""))
        sender = sender_address or str(email.get("sender") or "")
        domain = sender.split("@", 1)[1].lower() if "@" in sender else None
        email_id = str(email.get("id") or "")
        account_id = str(email.get("account_id") or "")
        provider = str(email.get("provider") or "unknown")
        preferred = preferred_unsubscribe_method(result.parsed_methods)
        http_method = next((method for method in result.parsed_methods if method.method in {"http", "https"}), None)
        mailto_method = next((method for method in result.parsed_methods if method.method == "mailto"), None)

        if not result.detected:
            return None

        return SubscriptionCandidate(
            id=f"{account_id}:{provider}:{email_id}:subscription",
            account_id=account_id,
            provider=provider,
            email_id=email_id,
            sender=sender,
            sender_domain=domain,
            display_name=sender_name or None,
            unsubscribe_supported=bool(preferred),
            unsubscribe_method="http" if preferred and preferred.method in {"http", "https"} else (preferred.method if preferred else None),
            unsubscribe_url=http_method.target if http_method else None,
            unsubscribe_email=mailto_method.target if mailto_method else None,
            list_id=result.list_id,
            evidence=[reason.removeprefix("header:") for reason in result.reasons],
            audit_metadata={
                "confidence": result.confidence,
                "source_headers": result.source_headers,
                "parsed_methods": [method.to_dict() for method in result.parsed_methods],
                "risk_recommendation": result.risk_recommendation,
            },
        )
