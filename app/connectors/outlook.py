from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.accounts import MailAccount
from app.core.models import EmailEntity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutlookConfig:
    tenant_id: str | None = None
    client_id_secret_name: str | None = None
    client_secret_name: str | None = None
    refresh_token_secret_name: str | None = None
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    scopes: tuple[str, ...] = ("Mail.Read", "offline_access")


@dataclass(frozen=True)
class OutlookAccount:
    account_id: str
    email: str
    secret_prefix: str
    max_emails: int = 25
    config: OutlookConfig = field(default_factory=OutlookConfig)

    @classmethod
    def from_mail_account(cls, account: MailAccount, config: OutlookConfig | None = None) -> "OutlookAccount":
        return cls(
            account_id=account.id,
            email=account.email,
            secret_prefix=account.secret_prefix,
            max_emails=account.max_emails,
            config=config or OutlookConfig(),
        )


class OutlookNormalizer:
    provider = "outlook"

    def to_email_entity(self, account: MailAccount, payload: dict[str, Any]) -> EmailEntity:
        sender = _format_email_address(payload.get("from", {}).get("emailAddress", {}))
        recipients = [
            _format_email_address(recipient.get("emailAddress", {}))
            for recipient in payload.get("toRecipients", [])
        ]
        recipients.extend(
            _format_email_address(recipient.get("emailAddress", {}))
            for recipient in payload.get("ccRecipients", [])
        )
        raw_headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in payload.get("internetMessageHeaders", [])
            if header.get("name")
        }

        return EmailEntity(
            id=payload["id"],
            provider=self.provider,
            account_id=account.id,
            account_email=account.email,
            thread_id=payload.get("conversationId"),
            subject=payload.get("subject") or "(sem assunto)",
            sender=sender,
            recipients=[recipient for recipient in recipients if recipient],
            snippet=payload.get("bodyPreview", ""),
            labels=list(payload.get("categories") or []),
            received_at=payload.get("receivedDateTime"),
            raw_headers=raw_headers,
            metadata={
                "outlook_change_key": payload.get("changeKey"),
                "outlook_importance": payload.get("importance"),
                "outlook_is_read": payload.get("isRead"),
                "outlook_web_link": payload.get("webLink"),
                "outlook_internet_message_id": payload.get("internetMessageId"),
            },
        )


class OutlookConnector:
    provider = "outlook"

    def __init__(
        self,
        *,
        enabled: bool = False,
        normalizer: OutlookNormalizer | None = None,
        graph_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        self.enabled = enabled
        self.normalizer = normalizer or OutlookNormalizer()
        self._graph_messages = graph_messages or []

    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        if not self.enabled:
            logger.info("OutlookConnector stub desabilitado para conta %s.", account.id)
            return []

        return [
            self.normalizer.to_email_entity(account, payload)
            for payload in self._graph_messages[: account.max_emails]
        ]


def _format_email_address(value: dict[str, Any]) -> str:
    address = value.get("address") or ""
    name = value.get("name") or ""
    if name and address:
        return f"{name} <{address}>"
    return address
