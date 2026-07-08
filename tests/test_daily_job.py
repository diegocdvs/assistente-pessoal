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


class FakeConnectorManager:
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
        self.saved_emails = []
        self.saved_classifications = []
        self.saved_action_plans = []
        self.saved_runs = []

    def save_email(self, email, run_id=None):
        self.saved_emails.append((email, run_id))
        return PersistenceResult(document_id=email.id, existed=False)

    def save_classification(self, email, classification, run_id=None):
        self.saved_classifications.append((email, classification, run_id))
        return email.id

    def save_action_plan(self, email, action_plan, run_id=None):
        self.saved_action_plans.append((email, action_plan, run_id))
        return email.id

    def save_run(self, report):
        self.saved_runs.append(report)
        return "run-1"


def test_daily_job_runs_decoupled_pipeline_and_report():
    connector_manager = FakeConnectorManager()
    persistence = FakePersistence()
    job = DailyJob(
        Settings(project_id="project", accounts_config_path="unused", dry_run=True),
        account_manager=FakeAccountManager(),
        connector_manager=connector_manager,
        persistence=persistence,
    )

    report = job.run()

    assert connector_manager.accounts == ["pessoal"]
    assert len(persistence.saved_emails) == 1
    assert len(persistence.saved_classifications) == 1
    assert len(persistence.saved_action_plans) == 2
    assert len(persistence.saved_runs) == 1
    assert report["schema_version"] == "0.2"
    assert report["run_id"].startswith("run-")
    assert persistence.saved_emails[0][1] == report["run_id"]
    assert persistence.saved_classifications[0][2] == report["run_id"]
    assert persistence.saved_action_plans[0][2] == report["run_id"]
    assert report["stage_counts"]["emails_fetched"] == 1
    assert report["stage_counts"]["work_items_created"] == 1
    assert report["stage_counts"]["classifications_created"] == 1
    assert report["stage_counts"]["action_plans_created"] == 2
    assert report["total_by_account"] == {"pessoal": 1}
    assert report["total_by_category"] == {"financeiro": 1}
    assert report["total_by_priority"] == {"alta": 1}
    assert report["planned_actions"][0]["dry_run"] is True
    assert report["planned_actions"][0]["id"] == "pessoal:msg-1:review_high_priority"
    assert report["errors"] == []
