from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Provider = Literal["gmail", "outlook"]


@dataclass(frozen=True)
class AccountPolicies:
    dry_run: bool = True
    mark_read_categories: list[str] = field(default_factory=list)
    never_mark_read_priorities: list[str] = field(default_factory=lambda: ["critica", "importante"])


@dataclass(frozen=True)
class MailAccount:
    id: str
    provider: Provider
    email: str
    enabled: bool
    secret_prefix: str
    max_emails: int = 25
    policies: AccountPolicies = field(default_factory=AccountPolicies)


def default_accounts() -> list[MailAccount]:
    return [
        MailAccount(
            id="pessoal_google",
            provider="gmail",
            email="diegocdvs13@gmail.com",
            enabled=True,
            secret_prefix="google-pessoal",
        )
    ]
