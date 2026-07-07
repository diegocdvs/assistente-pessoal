from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

Provider = Literal["gmail", "outlook"]


@dataclass(frozen=True)
class AccountPolicies:
    dry_run: bool = True
    mark_read_categories: list[str] = field(default_factory=list)
    never_mark_read_priorities: list[str] = field(default_factory=lambda: ["critica", "importante"])


@dataclass(frozen=True)
class MailAccount:
    id: str
    label: str
    provider: Provider
    email: str
    enabled: bool
    secret_prefix: str
    max_emails: int = 25
    calendar_enabled: bool = False
    firestore_enabled: bool = True
    policies: AccountPolicies = field(default_factory=AccountPolicies)


class AccountConfigError(ValueError):
    pass


class AccountManager:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self._accounts = self._load_accounts()

    def all_accounts(self) -> list[MailAccount]:
        return list(self._accounts)

    def enabled_accounts(self) -> list[MailAccount]:
        return [account for account in self._accounts if account.enabled]

    def enabled_by_provider(self, provider: Provider) -> list[MailAccount]:
        return [account for account in self.enabled_accounts() if account.provider == provider]

    def _load_accounts(self) -> list[MailAccount]:
        if not self.config_path.exists():
            raise AccountConfigError(f"Arquivo de contas nao encontrado: {self.config_path}")

        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        raw_accounts = data.get("accounts")
        if not isinstance(raw_accounts, list):
            raise AccountConfigError("config/accounts.yaml deve conter uma lista 'accounts'.")

        accounts = [self._parse_account(raw) for raw in raw_accounts]
        self._validate(accounts)
        return accounts

    def _parse_account(self, raw: dict) -> MailAccount:
        if not isinstance(raw, dict):
            raise AccountConfigError("Cada conta deve ser um objeto YAML.")

        provider = raw.get("provider")
        if provider not in {"gmail", "outlook"}:
            raise AccountConfigError(f"Provider invalido para conta {raw.get('id')!r}: {provider!r}")

        policies = raw.get("policies") or {}
        calendar = raw.get("calendar") or {}
        firestore = raw.get("firestore") or {}

        try:
            return MailAccount(
                id=str(raw["id"]),
                label=str(raw.get("label") or raw["id"]),
                provider=provider,
                email=str(raw["email"]),
                enabled=bool(raw.get("enabled", False)),
                secret_prefix=str(raw["secret_prefix"]),
                max_emails=int(raw.get("max_emails", 25)),
                calendar_enabled=bool(calendar.get("enabled", False)),
                firestore_enabled=bool(firestore.get("enabled", True)),
                policies=AccountPolicies(
                    dry_run=bool(policies.get("dry_run", True)),
                    mark_read_categories=list(policies.get("mark_read_categories") or []),
                    never_mark_read_priorities=list(
                        policies.get("never_mark_read_priorities") or ["critica", "importante"]
                    ),
                ),
            )
        except KeyError as exc:
            raise AccountConfigError(f"Campo obrigatorio ausente em conta: {exc.args[0]}") from exc

    def _validate(self, accounts: list[MailAccount]) -> None:
        seen_ids: set[str] = set()
        for account in accounts:
            if account.id in seen_ids:
                raise AccountConfigError(f"Conta duplicada: {account.id}")
            seen_ids.add(account.id)

            if account.max_emails < 1:
                raise AccountConfigError(f"max_emails deve ser maior que zero: {account.id}")
            if not account.email or "@" not in account.email:
                raise AccountConfigError(f"Email invalido para conta: {account.id}")
            if not account.secret_prefix:
                raise AccountConfigError(f"secret_prefix obrigatorio para conta: {account.id}")
