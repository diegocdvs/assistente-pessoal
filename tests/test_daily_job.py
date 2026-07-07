from __future__ import annotations

from app.config import Settings
from app.core.accounts import AccountPolicies, MailAccount
from app.core.daily_job import DailyJob
from app.core.models import EmailItem


class FakeAccountManager:
    def enabled_accounts(self):
        return [
            MailAccount(
                id="pessoal",
                label="Pessoal",
                provider="gmail",
                email="pessoal@example.com",
                enabled=True,
                secret_prefix="google-pessoal",
                max_emails=2,
                policies=AccountPolicies(),
            )
        ]


class FakeGmailConnector:
    def __init__(self):
        self.accounts = []

    def fetch_recent(self, account):
        self.accounts.append(account.id)
        return [
            EmailItem(
                account_id=account.id,
                account_email=account.email,
                provider=account.provider,
                id="msg-1",
                thread_id="thread-1",
                subject="Fatura vencimento hoje",
                sender="billing@example.com",
                recipients=[account.email],
                snippet="Pagamento via pix",
            )
        ]


class FakeStore:
    def __init__(self):
        self.saved_messages = []
        self.saved_runs = []

    def save_processed_emails(self, processed):
        self.saved_messages.extend(processed)
        return ["pessoal_gmail_msg-1"]

    def save_run(self, report):
        self.saved_runs.append(report)
        return "run-1"


def test_daily_job_reads_enabled_gmail_accounts_and_persists_messages():
    gmail = FakeGmailConnector()
    store = FakeStore()
    job = DailyJob(
        Settings(project_id="project", accounts_config_path="unused"),
        account_manager=FakeAccountManager(),
        gmail_connector=gmail,
        store=store,
    )

    report = job.run()

    assert gmail.accounts == ["pessoal"]
    assert len(store.saved_messages) == 1
    assert len(store.saved_runs) == 1
    assert report["total"] == 1
    assert report["important_count"] == 1
    assert report["errors"] == []
