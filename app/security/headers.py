from __future__ import annotations

from email.utils import parseaddr
from typing import Any

from app.security.models import HeaderAssessment


class HeaderAnalyzer:
    def analyze(self, headers: dict[str, Any] | None) -> HeaderAssessment:
        normalized = _normalize_headers(headers)
        sender = _address(normalized.get("from", ""))
        reply_to = _address(normalized.get("reply-to", ""))
        return_path = _address(normalized.get("return-path", ""))
        authentication_results = normalized.get("authentication-results", "")

        suspicious: list[str] = []
        spoofing: list[str] = []
        authentication: list[str] = []

        if reply_to and sender and reply_to.split("@")[-1] != sender.split("@")[-1]:
            spoofing.append("reply_to_domain_differs")
        if return_path and sender and return_path.split("@")[-1] != sender.split("@")[-1]:
            spoofing.append("return_path_domain_differs")

        for signal in ("spf", "dkim", "dmarc"):
            status = _auth_status(authentication_results, signal)
            if status:
                authentication.append(f"{signal}:{status}")
                if status not in {"pass", "bestguesspass"}:
                    spoofing.append(f"{signal}:{status}")

        if normalized.get("x-priority") == "1":
            suspicious.append("x_priority_high")
        if "x-ms-exchange-organization-authas" in normalized and "anonymous" in normalized.get("x-ms-exchange-organization-authas", "").lower():
            suspicious.append("exchange_auth_anonymous")

        return HeaderAssessment(
            list_unsubscribe=bool(normalized.get("list-unsubscribe")),
            list_id=bool(normalized.get("list-id")),
            auto_submitted=normalized.get("auto-submitted"),
            precedence=normalized.get("precedence"),
            reply_to_differs=bool(reply_to and sender and reply_to != sender),
            return_path=return_path or None,
            authentication_signals=authentication,
            spoofing_signals=sorted(set(spoofing)),
            suspicious_headers=sorted(set(suspicious)),
        )


def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(headers, dict):
        return {}
    return {str(key).strip().lower(): str(value).strip() for key, value in headers.items()}


def _address(value: str) -> str:
    return parseaddr(value)[1].lower()


def _auth_status(authentication_results: str, signal: str) -> str | None:
    lowered = authentication_results.lower()
    marker = f"{signal}="
    if marker not in lowered:
        return None
    return lowered.split(marker, 1)[1].split()[0].strip(";")
