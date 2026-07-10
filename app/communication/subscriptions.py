from __future__ import annotations

import re
from email.utils import parseaddr
from typing import Any
from urllib.parse import urlparse

from app.communication.models import SubscriptionCandidate

_LIST_UNSUBSCRIBE_RE = re.compile(r"<([^>]+)>")


class SubscriptionDetector:
    """Detect subscription candidates without accessing external URLs."""

    def detect(self, emails: list[dict[str, Any]]) -> list[SubscriptionCandidate]:
        candidates: list[SubscriptionCandidate] = []
        for email in emails:
            candidate = self._from_email(email)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _from_email(self, email: dict[str, Any]) -> SubscriptionCandidate | None:
        headers = _normalized_headers(email.get("raw_headers"))
        list_unsubscribe = headers.get("list-unsubscribe", "")
        list_id = headers.get("list-id")
        precedence = headers.get("precedence", "").lower()
        auto_submitted = headers.get("auto-submitted", "").lower()

        evidence: list[str] = []
        if list_unsubscribe:
            evidence.append("list-unsubscribe")
        if list_id:
            evidence.append("list-id")
        if precedence in {"bulk", "list", "junk"}:
            evidence.append(f"precedence:{precedence}")
        if auto_submitted and auto_submitted != "no":
            evidence.append("auto-submitted")

        if not evidence:
            return None

        unsubscribe_url, unsubscribe_email, method = _parse_unsubscribe(list_unsubscribe)
        sender_name, sender_address = parseaddr(str(email.get("sender") or ""))
        sender = sender_address or str(email.get("sender") or "")
        domain = sender.split("@", 1)[1].lower() if "@" in sender else None
        email_id = str(email.get("id") or "")
        account_id = str(email.get("account_id") or "")
        provider = str(email.get("provider") or "unknown")

        return SubscriptionCandidate(
            id=f"{account_id}:{provider}:{email_id}:subscription",
            account_id=account_id,
            provider=provider,
            email_id=email_id,
            sender=sender,
            sender_domain=domain,
            display_name=sender_name or None,
            unsubscribe_supported=bool(method),
            unsubscribe_method=method,
            unsubscribe_url=unsubscribe_url,
            unsubscribe_email=unsubscribe_email,
            list_id=list_id,
            evidence=evidence,
            audit_metadata={
                "list_unsubscribe_post": headers.get("list-unsubscribe-post"),
                "precedence": headers.get("precedence"),
            },
        )


def _normalized_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key).strip().lower(): str(item).strip() for key, item in value.items()}


def _parse_unsubscribe(value: str) -> tuple[str | None, str | None, str | None]:
    if not value:
        return None, None, None

    entries = _LIST_UNSUBSCRIBE_RE.findall(value) or [part.strip() for part in value.split(",")]
    safe_http_url: str | None = None
    mailto_address: str | None = None

    for entry in entries:
        item = entry.strip()
        parsed = urlparse(item)
        if parsed.scheme in {"https", "http"} and parsed.netloc and safe_http_url is None:
            safe_http_url = item
        elif parsed.scheme == "mailto" and parsed.path and mailto_address is None:
            mailto_address = parsed.path

    if safe_http_url:
        return safe_http_url, mailto_address, "http"
    if mailto_address:
        return None, mailto_address, "mailto"
    return None, None, None
