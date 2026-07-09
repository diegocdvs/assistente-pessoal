from __future__ import annotations

import pytest

from app.auth.microsoft import MicrosoftOAuthProvider
from app.auth.oauth import OAuthTokenError
from app.core.accounts import MailAccount


class FakeSecretReader:
    def __init__(self, values):
        self.values = values
        self.names = []

    def read_text(self, name):
        self.names.append(name)
        return self.values[name]


class FakeTokenCache:
    def __init__(self):
        self.serialized = None

    def deserialize(self, value):
        self.serialized = value


class FakeConfidentialClientApplication:
    accounts = [{"username": "user@example.com"}]
    result = {"access_token": "graph-token"}
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.silent_calls = []
        FakeConfidentialClientApplication.instances.append(self)

    def get_accounts(self):
        return self.accounts

    def acquire_token_silent(self, scopes, account):
        self.silent_calls.append((scopes, account))
        return self.result


def make_account() -> MailAccount:
    return MailAccount(
        id="outlook_profissional",
        label="Outlook Profissional",
        provider="outlook",
        email="profissional@example.com",
        enabled=True,
        secret_prefix="outlook-profissional",
    )


def make_secret_reader() -> FakeSecretReader:
    return FakeSecretReader(
        {
            "outlook-profissional-tenant-id": "tenant-id",
            "outlook-profissional-client-id": "client-id",
            "outlook-profissional-client-secret": "client-secret",
            "outlook-profissional-token-cache": '{"AccessToken": {}}',
        }
    )


def test_microsoft_oauth_provider_uses_msal_cache_and_silent_token(monkeypatch):
    FakeConfidentialClientApplication.instances = []
    monkeypatch.setattr("app.auth.microsoft.msal.SerializableTokenCache", FakeTokenCache)
    monkeypatch.setattr(
        "app.auth.microsoft.msal.ConfidentialClientApplication",
        FakeConfidentialClientApplication,
    )

    provider = MicrosoftOAuthProvider(secret_reader=make_secret_reader())

    token = provider.get_access_token(make_account())

    app = FakeConfidentialClientApplication.instances[0]
    assert token == "graph-token"
    assert app.kwargs["client_id"] == "client-id"
    assert app.kwargs["authority"] == "https://login.microsoftonline.com/tenant-id"
    assert app.kwargs["client_credential"] == "client-secret"
    assert app.kwargs["token_cache"].serialized == '{"AccessToken": {}}'
    assert app.silent_calls == [(["https://graph.microsoft.com/Mail.Read"], {"username": "user@example.com"})]


def test_microsoft_oauth_provider_fails_when_cache_has_no_account(monkeypatch):
    class NoAccountClient(FakeConfidentialClientApplication):
        accounts = []

    monkeypatch.setattr("app.auth.microsoft.msal.SerializableTokenCache", FakeTokenCache)
    monkeypatch.setattr("app.auth.microsoft.msal.ConfidentialClientApplication", NoAccountClient)

    provider = MicrosoftOAuthProvider(secret_reader=make_secret_reader())

    with pytest.raises(OAuthTokenError, match="nao contem conta delegada"):
        provider.get_access_token(make_account())


def test_microsoft_oauth_provider_fails_when_silent_token_fails(monkeypatch):
    class FailingClient(FakeConfidentialClientApplication):
        accounts = [{"username": "user@example.com"}]
        result = {"error": "invalid_grant", "error_description": "expired"}

    monkeypatch.setattr("app.auth.microsoft.msal.SerializableTokenCache", FakeTokenCache)
    monkeypatch.setattr("app.auth.microsoft.msal.ConfidentialClientApplication", FailingClient)

    provider = MicrosoftOAuthProvider(secret_reader=make_secret_reader())

    with pytest.raises(OAuthTokenError, match="invalid_grant"):
        provider.get_access_token(make_account())


def test_microsoft_oauth_provider_wraps_missing_secret():
    provider = MicrosoftOAuthProvider(secret_reader=FakeSecretReader({}))

    with pytest.raises(OAuthTokenError, match="Secret Microsoft indisponivel"):
        provider.get_access_token(make_account())
