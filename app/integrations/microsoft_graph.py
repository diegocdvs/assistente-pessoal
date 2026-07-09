from __future__ import annotations

from typing import Any

import requests


class MicrosoftGraphError(RuntimeError):
    pass


class MicrosoftGraphMailClient:
    def __init__(
        self,
        *,
        base_url: str = "https://graph.microsoft.com/v1.0",
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def fetch_recent_messages(self, *, access_token: str, max_results: int) -> list[dict[str, Any]]:
        response = self.session.get(
            f"{self.base_url}/me/messages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            params={
                "$top": max_results,
                "$orderby": "receivedDateTime desc",
                "$select": ",".join(
                    [
                        "id",
                        "conversationId",
                        "changeKey",
                        "internetMessageId",
                        "subject",
                        "bodyPreview",
                        "receivedDateTime",
                        "importance",
                        "isRead",
                        "webLink",
                        "categories",
                        "from",
                        "toRecipients",
                        "ccRecipients",
                        "internetMessageHeaders",
                    ]
                ),
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise MicrosoftGraphError(
                f"Microsoft Graph /me/messages falhou com HTTP {response.status_code}: {response.text}"
            )

        payload = response.json()
        value = payload.get("value", [])
        if not isinstance(value, list):
            raise MicrosoftGraphError("Resposta Microsoft Graph invalida: campo 'value' nao e lista.")
        return value
