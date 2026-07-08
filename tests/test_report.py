from __future__ import annotations

from datetime import datetime, timezone

from app.core.accounts import MailAccount
from app.core.models import ActionPlan, Category, Classification, EmailEntity, PipelineResult, Priority
from app.core.report import Reporter


def test_reporter_summarizes_pipeline_results():
    account = MailAccount(
        id="acc",
        label="Conta",
        provider="gmail",
        email="acc@example.com",
        enabled=True,
        secret_prefix="secret",
    )
    email = EmailEntity(
        id="msg-1",
        provider="gmail",
        account_id="acc",
        account_email="acc@example.com",
        thread_id=None,
        subject="Fatura",
        sender="sender@example.com",
        recipients=["acc@example.com"],
        snippet="Pagamento",
    )
    result = PipelineResult(
        email=email,
        classification=Classification(Category.FINANCEIRO, Priority.ALTA, 0.8, "Financeiro."),
        action_plans=[ActionPlan("review_financial", "Revisar.", True, payload={"email_id": "msg-1"})],
    )

    report = Reporter().build(
        started_at=datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 8, 10, 0, 5, tzinfo=timezone.utc),
        dry_run=True,
        accounts=[account],
        results=[result],
        errors=[],
    )

    assert report["total_by_account"] == {"acc": 1}
    assert report["total_by_category"] == {"financeiro": 1}
    assert report["total_by_priority"] == {"alta": 1}
    assert report["duration_seconds"] == 5.0
    assert report["planned_actions"][0]["type"] == "review_financial"
