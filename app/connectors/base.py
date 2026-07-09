from __future__ import annotations

from typing import Protocol

from app.core.accounts import MailAccount
from app.core.models import EmailEntity


class Connector(Protocol):
    provider: str

    def fetch_recent(self, account: MailAccount) -> list[EmailEntity]:
        pass
