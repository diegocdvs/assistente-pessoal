from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from typing import Any, Protocol

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.connectors.secrets import SecretReader
from app.daily_brief_delivery.models import DailyBriefEmailMessage

GMAIL_DRAFT_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class DailyBriefDeliveryClient(Protocol):
    def create_draft(self, message: DailyBriefEmailMessage) -> dict[str, Any]:
        pass

    def send_message(self, message: DailyBriefEmailMessage) -> dict[str, Any]:
        pass


class NoopDailyBriefDeliveryClient:
    def create_draft(self, message: DailyBriefEmailMessage) -> dict[str, Any]:
        return {"id": f"noop-draft:{message.message_id}"}

    def send_message(self, message: DailyBriefEmailMessage) -> dict[str, Any]:
        return {"id": f"noop-message:{message.message_id}"}


class GmailDailyBriefDeliveryClient:
    def __init__(
        self,
        *,
        project_id: str,
        secret_prefix: str,
        scopes: list[str] | None = None,
        secret_reader: SecretReader | None = None,
        service: Any | None = None,
    ) -> None:
        self.project_id = project_id
        self.secret_prefix = secret_prefix
        self.scopes = scopes or [GMAIL_DRAFT_SCOPE]
        self.secret_reader = secret_reader or SecretReader(project_id)
        self._service = service

    def create_draft(self, message: DailyBriefEmailMessage) -> dict[str, Any]:
        raw = _encode_message(message)
        return (
            self._build_service()
            .users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )

    def send_message(self, message: DailyBriefEmailMessage) -> dict[str, Any]:
        raw = _encode_message(message)
        return self._build_service().users().messages().send(userId="me", body={"raw": raw}).execute()

    def _build_service(self) -> Any:
        if self._service is not None:
            return self._service

        client_config = json.loads(self.secret_reader.read_text(f"{self.secret_prefix}-client-secret-json"))
        refresh_token = self.secret_reader.read_text(f"{self.secret_prefix}-refresh-token").strip()
        installed = client_config.get("installed") or client_config.get("web") or {}
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=installed.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=installed["client_id"],
            client_secret=installed["client_secret"],
            scopes=self.scopes,
        )
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service


def _encode_message(message: DailyBriefEmailMessage) -> str:
    email = EmailMessage()
    email["To"] = message.recipient
    email["Subject"] = message.subject
    email["X-Assistente-Pessoal-Idempotency-Key"] = message.idempotency_key
    email.set_content(message.text_body)
    email.add_alternative(message.html_body, subtype="html")
    return base64.urlsafe_b64encode(email.as_bytes()).decode("utf-8")
