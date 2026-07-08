from __future__ import annotations

import json
import logging
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.connectors.secrets import SecretReader
from app.core.accounts import MailAccount
from app.core.models import EmailEntity

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailConnector:
    def __init__(self, project_id: str, secret_reader: SecretReader | None = None) -> None:
        self.project_id = project_id
        self.secret_reader = secret_reader or SecretReader(project_id)

    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        service = self._build_service(account)
        response = service.users().messages().list(
            userId="me",
            maxResults=account.max_emails,
            q="-in:trash",
        ).execute()

        messages = response.get("messages", [])
        logger.info("Gmail retornou %s mensagens para conta %s", len(messages), account.id)

        emails: list[EmailEntity] = []
        for message in messages:
            payload = service.users().messages().get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Cc", "Subject", "Date"],
            ).execute()
            emails.append(self._to_email_entity(account, payload))
        return emails

    def _build_service(self, account: MailAccount) -> Any:
        client_config = json.loads(self.secret_reader.read_text(f"{account.secret_prefix}-client-secret-json"))
        refresh_token = self.secret_reader.read_text(f"{account.secret_prefix}-refresh-token").strip()

        installed = client_config.get("installed") or client_config.get("web") or {}
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=installed.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=installed["client_id"],
            client_secret=installed["client_secret"],
            scopes=GMAIL_SCOPES,
        )
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def _to_email_entity(self, account: MailAccount, payload: dict[str, Any]) -> EmailEntity:
        headers = {
            header["name"].lower(): _decode_header_value(header.get("value", ""))
            for header in payload.get("payload", {}).get("headers", [])
        }
        recipients = [
            value
            for value in [headers.get("to", ""), headers.get("cc", "")]
            if value
        ]

        return EmailEntity(
            id=payload["id"],
            provider=account.provider,
            account_id=account.id,
            account_email=account.email,
            thread_id=payload.get("threadId"),
            subject=headers.get("subject", "(sem assunto)"),
            sender=headers.get("from", ""),
            recipients=recipients,
            snippet=payload.get("snippet", ""),
            labels=payload.get("labelIds", []),
            received_at=_received_at(headers.get("date"), payload.get("internalDate")),
            raw_headers=headers,
            metadata={
                "gmail_internal_date": payload.get("internalDate"),
                "gmail_history_id": payload.get("historyId"),
                "gmail_size_estimate": payload.get("sizeEstimate"),
            },
        )


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    decoded: list[str] = []
    for content, encoding in parts:
        if isinstance(content, bytes):
            decoded.append(content.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(content)
    return "".join(decoded)


def _received_at(date_header: str | None, internal_date: str | None) -> str | None:
    if date_header:
        try:
            return parsedate_to_datetime(date_header).isoformat()
        except (TypeError, ValueError):
            pass

    if internal_date:
        try:
            return str(_millis_to_iso(internal_date))
        except ValueError:
            return None
    return None


def _millis_to_iso(value: str) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
