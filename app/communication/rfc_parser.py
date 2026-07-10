from __future__ import annotations

import re
from email.utils import parseaddr
from typing import Any
from urllib.parse import urlparse

from app.communication.models import UnsubscribeMethod

SUBSCRIPTION_HEADERS = (
    "list-unsubscribe",
    "list-unsubscribe-post",
    "list-id",
    "list-post",
    "precedence",
    "auto-submitted",
    "reply-to",
    "return-path",
)

_ANGLE_VALUE_RE = re.compile(r"<([^>]+)>")
_ONE_CLICK_VALUE = "list-unsubscribe=one-click"


def normalize_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key).strip().lower(): str(item).strip() for key, item in value.items()}


def source_subscription_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    normalized = normalize_headers(headers)
    return {
        key: value
        for key, value in normalized.items()
        if key in SUBSCRIPTION_HEADERS and value
    }


def parse_unsubscribe_methods(headers: dict[str, Any] | None) -> list[UnsubscribeMethod]:
    normalized = normalize_headers(headers)
    raw_value = normalized.get("list-unsubscribe", "")
    one_click = _ONE_CLICK_VALUE in normalized.get("list-unsubscribe-post", "").lower()
    methods: list[UnsubscribeMethod] = []
    seen: set[tuple[str, str]] = set()

    for entry in _split_list_unsubscribe(raw_value):
        parsed = urlparse(entry)
        scheme = parsed.scheme.lower()
        method: UnsubscribeMethod | None = None
        if scheme in {"http", "https"} and parsed.netloc:
            method = UnsubscribeMethod(
                method=scheme,
                target=entry,
                redacted_target=_redact_url(entry),
                one_click=one_click,
            )
        elif scheme == "mailto" and parsed.path:
            address = parseaddr(parsed.path)[1] or parsed.path
            method = UnsubscribeMethod(
                method="mailto",
                target=address,
                redacted_target=_redact_email(address),
                one_click=False,
            )

        if method is None:
            continue
        identity = (method.method, method.target.lower())
        if identity not in seen:
            seen.add(identity)
            methods.append(method)

    return methods


def preferred_unsubscribe_method(methods: list[UnsubscribeMethod]) -> UnsubscribeMethod | None:
    for method in methods:
        if method.one_click and method.method == "https":
            return method
    for method in methods:
        if method.method == "https":
            return method
    for method in methods:
        if method.method == "http":
            return method
    return methods[0] if methods else None


def extract_list_id(headers: dict[str, Any] | None) -> str | None:
    value = normalize_headers(headers).get("list-id")
    if not value:
        return None
    match = _ANGLE_VALUE_RE.search(value)
    return (match.group(1) if match else value).strip() or None


def _split_list_unsubscribe(value: str) -> list[str]:
    if not value:
        return []
    entries = _ANGLE_VALUE_RE.findall(value)
    if not entries:
        entries = [part.strip() for part in value.split(",")]
    return [entry.strip() for entry in entries if entry.strip()]


def _redact_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return "[redacted-url]"
    return f"{parsed.scheme}://{parsed.netloc}/[redacted]"


def _redact_email(value: str) -> str:
    local, sep, domain = value.partition("@")
    if not sep:
        return "[redacted-email]"
    prefix = local[:1] + "***" if local else "***"
    return f"{prefix}@{domain}"
