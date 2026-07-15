from __future__ import annotations

import hashlib

from app.core.models import SCHEMA_VERSION


CHANNEL_EMAIL = "email"


def build_scheduled_idempotency_key(
    *,
    schedule_date: str,
    timezone_name: str,
    account_scope: str,
    delivery_mode: str,
    recipient: str,
    channel: str = CHANNEL_EMAIL,
    schema_version: str = SCHEMA_VERSION,
) -> str:
    material = "|".join(
        [
            schedule_date,
            timezone_name,
            account_scope or "all",
            channel,
            delivery_mode,
            normalize_recipient(recipient),
            schema_version,
        ]
    )
    return f"scheduled-daily-brief:{hashlib.sha256(material.encode('utf-8')).hexdigest()[:40]}"


def hash_recipient(recipient: str) -> str:
    normalized = normalize_recipient(recipient)
    if not normalized:
        return "recipient:none"
    return f"recipient:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"


def redact_recipient(recipient: str | None) -> str:
    normalized = normalize_recipient(recipient or "")
    if not normalized or "@" not in normalized:
        return "(none)"
    local, domain = normalized.split("@", 1)
    prefix = local[:2] if len(local) > 2 else local[:1]
    return f"{prefix}***@{domain}"


def redact_key(value: str) -> str:
    if len(value) <= 16:
        return value
    return f"{value[:12]}...{value[-6:]}"


def normalize_recipient(recipient: str) -> str:
    return recipient.strip().lower()
