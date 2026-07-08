from __future__ import annotations

from app.config import Settings
from app.core.accounts import AccountPolicies, MailAccount
from app.core.daily_job import DailyJob
from app.core.models import EmailEntity
from app.storage.persistence import PersistenceResult


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
            EmailEntity(
                id="msg-1",
                provider=account.provider,
                account_id=account.id,
                account_email=account.email,
                thread_id="thread-1",
                subject="Fatura vencimento hoje",
                sender="billing@example.com",
                recipients=[account.email],
                snippet="Pagamento via pix",
            )
        ]


class FakePersistence:
    def __init__(self):
        self.upserts = []
        self.saved_runs = []

    def upsert_email(self, email, classification, actions):
        self.upserts.append((email, classification, actions))
        return PersistenceResult(email_id=email.id, existed=False)

    def save_run(self, report):
        self.saved_runs.append(report)
        return "run-1"


def test_daily_job_runs_full_pipeline_and_report():
    gmail = FakeGmailConnector()
    persistence = FakePersistence()
    job = DailyJob(
        Settings(project_id="project", accounts_config_path="unused", dry_run=True),
        account_manager=FakeAccountManager(),
        gmail_connector=gmail,
        persistence=persistence,
    )

    report = job.run()

    assert gmail.accounts == ["pessoal"]
    assert len(persistence.upserts) == 1
    assert len(persistence.saved_runs) == 1
    assert report["total"] == 1
    assert report["total_by_account"] == {"pessoal": 1}
    assert report["total_by_category"] == {"financeiro": 1}
    assert report["total_by_priority"] == {"alta": 1}
    assert report["planned_actions"][0]["dry_run"] is True
    assert report["errors"] == []
