from __future__ import annotations

import pytest

from app.core.accounts import AccountConfigError, AccountManager


def test_account_manager_loads_enabled_accounts(tmp_path):
    config = tmp_path / "accounts.yaml"
    config.write_text(
        """
accounts:
  - id: pessoal
    label: Pessoal
    provider: gmail
    email: pessoa@example.com
    enabled: true
    secret_prefix: google-pessoal
    max_emails: 7
    calendar:
      enabled: true
    firestore:
      enabled: true
    policies:
      dry_run: true
      mark_read_categories:
        - promocoes
      never_mark_read_priorities:
        - critica
  - id: trabalho
    provider: gmail
    email: trabalho@example.com
    enabled: false
    secret_prefix: google-trabalho
""",
        encoding="utf-8",
    )

    manager = AccountManager(config)

    enabled = manager.enabled_accounts()
    assert len(enabled) == 1
    assert enabled[0].id == "pessoal"
    assert enabled[0].max_emails == 7
    assert enabled[0].calendar_enabled is True
    assert enabled[0].policies.mark_read_categories == ["promocoes"]


def test_account_manager_rejects_duplicate_ids(tmp_path):
    config = tmp_path / "accounts.yaml"
    config.write_text(
        """
accounts:
  - id: mesma
    provider: gmail
    email: um@example.com
    enabled: true
    secret_prefix: google-um
  - id: mesma
    provider: gmail
    email: dois@example.com
    enabled: true
    secret_prefix: google-dois
""",
        encoding="utf-8",
    )

    with pytest.raises(AccountConfigError, match="duplicada"):
        AccountManager(config)
