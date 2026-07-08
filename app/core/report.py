from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from app.core.accounts import MailAccount
from app.core.models import PipelineResult


class Reporter:
    def build(
        self,
        *,
        started_at: datetime,
        finished_at: datetime,
        dry_run: bool,
        accounts: list[MailAccount],
        results: list[PipelineResult],
        errors: list[dict[str, str]],
    ) -> dict[str, Any]:
        by_account = Counter(result.email.account_id for result in results)
        by_category = Counter(result.classification.category.value for result in results)
        by_priority = Counter(result.classification.priority.value for result in results)
        planned_actions = [
            {
                "account_id": result.email.account_id,
                "email_id": result.email.id,
                **action.to_dict(),
            }
            for result in results
            for action in result.action_plans
        ]

        return {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "dry_run": dry_run,
            "accounts_total": len(accounts),
            "accounts": [
                {
                    "id": account.id,
                    "label": account.label,
                    "provider": account.provider,
                    "email": account.email,
                    "max_emails": account.max_emails,
                }
                for account in accounts
            ],
            "total": len(results),
            "total_by_account": dict(by_account),
            "total_by_category": dict(by_category),
            "total_by_priority": dict(by_priority),
            "errors": errors,
            "planned_actions": planned_actions,
        }
