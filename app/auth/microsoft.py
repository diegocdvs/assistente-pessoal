from __future__ import annotations

from dataclasses import dataclass

import msal

from app.auth.oauth import OAuthTokenError
from app.connectors.secrets import SecretReader
from app.core.accounts import MailAccount

DEFAULT_GRAPH_SCOPES = ("https://graph.microsoft.com/Mail.Read",)


@dataclass(frozen=True)
class MicrosoftOAuthConfig:
    tenant_id_secret_name: str
    client_id_secret_name: str
    client_secret_name: str
    token_cache_secret_name: str
    scopes: tuple[str, ...] = DEFAULT_GRAPH_SCOPES

    @classmethod
    def from_account(cls, account: MailAccount) -> "MicrosoftOAuthConfig":
        return cls(
            tenant_id_secret_name=f"{account.secret_prefix}-tenant-id",
            client_id_secret_name=f"{account.secret_prefix}-client-id",
            client_secret_name=f"{account.secret_prefix}-client-secret",
            token_cache_secret_name=f"{account.secret_prefix}-token-cache",
        )


class MicrosoftOAuthProvider:
    def __init__(
        self,
        *,
        secret_reader: SecretReader,
        scopes: tuple[str, ...] = DEFAULT_GRAPH_SCOPES,
    ) -> None:
        self.secret_reader = secret_reader
        self.scopes = scopes

    def get_access_token(self, account: MailAccount) -> str:
        config = MicrosoftOAuthConfig.from_account(account)
        tenant_id = self._read_secret(config.tenant_id_secret_name)
        client_id = self._read_secret(config.client_id_secret_name)
        client_secret = self._read_secret(config.client_secret_name)
        serialized_cache = self._read_secret(config.token_cache_secret_name)

        cache = msal.SerializableTokenCache()
        if serialized_cache.strip():
            cache.deserialize(serialized_cache)

        client = msal.ConfidentialClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
            token_cache=cache,
        )

        accounts = client.get_accounts()
        if not accounts:
            raise OAuthTokenError(
                f"Token cache Microsoft nao contem conta delegada para {account.id}. "
                "Execute o bootstrap OAuth e grave o token cache no Secret Manager."
            )

        result = client.acquire_token_silent(list(self.scopes), account=accounts[0])
        access_token = result.get("access_token") if isinstance(result, dict) else None
        if access_token:
            return access_token

        error = result.get("error") if isinstance(result, dict) else "token_unavailable"
        description = result.get("error_description") if isinstance(result, dict) else ""
        raise OAuthTokenError(f"Falha ao obter token Microsoft via MSAL: {error} {description}".strip())

    def _read_secret(self, name: str) -> str:
        try:
            return self.secret_reader.read_text(name).strip()
        except Exception as exc:
            raise OAuthTokenError(f"Secret Microsoft indisponivel: {name}") from exc
