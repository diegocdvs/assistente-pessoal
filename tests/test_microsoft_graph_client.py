from __future__ import annotations

import pytest

from app.integrations.microsoft_graph import MicrosoftGraphError, MicrosoftGraphMailClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {"value": []}
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, *, headers, params, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return self.response


def test_microsoft_graph_mail_client_fetches_recent_messages():
    session = FakeSession(FakeResponse(payload={"value": [{"id": "message-1"}]}))
    client = MicrosoftGraphMailClient(base_url="https://graph.example/v1.0/", session=session)

    messages = client.fetch_recent_messages(access_token="token-123", max_results=5)

    assert messages == [{"id": "message-1"}]
    call = session.calls[0]
    assert call["url"] == "https://graph.example/v1.0/me/messages"
    assert call["headers"]["Authorization"] == "Bearer token-123"
    assert call["params"]["$top"] == 5
    assert call["params"]["$orderby"] == "receivedDateTime desc"
    assert "internetMessageHeaders" in call["params"]["$select"]
    assert call["timeout"] == 30


def test_microsoft_graph_mail_client_raises_on_http_error():
    session = FakeSession(FakeResponse(status_code=403, text="forbidden"))
    client = MicrosoftGraphMailClient(session=session)

    with pytest.raises(MicrosoftGraphError, match="HTTP 403"):
        client.fetch_recent_messages(access_token="token-123", max_results=5)


def test_microsoft_graph_mail_client_rejects_invalid_payload():
    session = FakeSession(FakeResponse(payload={"value": {"id": "message-1"}}))
    client = MicrosoftGraphMailClient(session=session)

    with pytest.raises(MicrosoftGraphError, match="value"):
        client.fetch_recent_messages(access_token="token-123", max_results=5)
