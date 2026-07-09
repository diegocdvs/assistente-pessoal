from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.auth.oauth import OAuthProvider, StaticOAuthProvider
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


class OutlookMessageClient(Protocol):
    def fetch_recent_messages(self, *, access_token: str, max_results: int) -> list[dict[str, Any]]:
        pass


@dataclass
class StaticOutlookMessageClient:
    messages: list[dict[str, Any]]

    def fetch_recent_messages(self, *, access_token: str, max_results: int) -> list[dict[str, Any]]:
        return self.messages[:max_results]


class OutlookConnector:
    provider = "outlook"

    def __init__(
        self,
        *,
        enabled: bool = False,
        normalizer: OutlookNormalizer | None = None,
        oauth_provider: OAuthProvider | None = None,
        message_client: OutlookMessageClient | None = None,
        graph_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        self.enabled = enabled
        self.normalizer = normalizer or OutlookNormalizer()
        self.oauth_provider = oauth_provider
        self.message_client = message_client
        if graph_messages is not None:
            self.oauth_provider = self.oauth_provider or StaticOAuthProvider()
            self.message_client = self.message_client or StaticOutlookMessageClient(graph_messages)

    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        if not self.enabled:
            logger.info("OutlookConnector desabilitado para conta %s.", account.id)
            return []

        if self.oauth_provider is None or self.message_client is None:
            raise RuntimeError("OutlookConnector habilitado sem OAuthProvider ou cliente de mensagens.")

        access_token = self.oauth_provider.get_access_token(account)
        graph_messages = self.message_client.fetch_recent_messages(
            access_token=access_token,
            max_results=account.max_emails,
        )

        return [
            self.normalizer.to_email_entity(account, payload)
            for payload in graph_messages
        ]


def _format_email_address(value: dict[str, Any]) -> str:
    address = value.get("address") or ""
    name = value.get("name") or ""
    if name and address:
        return f"{name} <{address}>"
    return address
