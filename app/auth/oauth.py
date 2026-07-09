from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.accounts import MailAccount


class OAuthTokenError(RuntimeError):
    pass


class OAuthProvider(Protocol):
    def get_access_token(self, account: MailAccount) -> str:
        pass


@dataclass(frozen=True)
class StaticOAuthProvider:
    access_token: str = "test-access-token"

    def get_access_token(self, account: MailAccount) -> str:
        return self.access_token
