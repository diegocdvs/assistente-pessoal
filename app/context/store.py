from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from google.cloud import firestore


@dataclass(frozen=True)
class ContextData:
    emails: list[dict[str, Any]] = field(default_factory=list)
    classifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    action_plans: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    reports: list[dict[str, Any]] = field(default_factory=list)


class ContextRepository(Protocol):
    def load_context_data(self, *, account_ids: list[str] | None = None, limit: int = 100) -> ContextData:
        pass


class InMemoryContextRepository:
    def __init__(
        self,
        *,
        emails: list[dict[str, Any]] | None = None,
        classifications: dict[str, dict[str, Any]] | None = None,
        action_plans: dict[str, list[dict[str, Any]]] | None = None,
        reports: list[dict[str, Any]] | None = None,
    ) -> None:
        self.data = ContextData(
            emails=emails or [],
            classifications=classifications or {},
            action_plans=action_plans or {},
            reports=reports or [],
        )

    def load_context_data(self, *, account_ids: list[str] | None = None, limit: int = 100) -> ContextData:
        if account_ids is None:
            return self.data
        allowed = set(account_ids)
        emails = [email for email in self.data.emails if email.get("account_id") in allowed]
        message_ids = {str(email.get("id")) for email in emails}
        return ContextData(
            emails=emails[:limit],
            classifications={
                message_id: classification
                for message_id, classification in self.data.classifications.items()
                if message_id in message_ids
            },
            action_plans={
                message_id: plans
                for message_id, plans in self.data.action_plans.items()
                if message_id in message_ids
            },
            reports=[
                report
                for report in self.data.reports
                if _report_intersects_accounts(report, allowed)
            ][:limit],
        )


class FirestoreContextRepository:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def load_context_data(self, *, account_ids: list[str] | None = None, limit: int = 100) -> ContextData:
        account_documents = self._account_documents(account_ids)
        emails: list[dict[str, Any]] = []
        classifications: dict[str, dict[str, Any]] = {}
        action_plans: dict[str, list[dict[str, Any]]] = {}

        for account_doc in account_documents:
            for email_doc in account_doc.collection("emails").limit(limit).stream():
                payload = email_doc.to_dict() or {}
                payload.setdefault("id", email_doc.id)
                payload.setdefault("account_id", account_doc.id)
                emails.append(payload)

            for classification_doc in account_doc.collection("classifications").limit(limit).stream():
                payload = classification_doc.to_dict() or {}
                message_id = str(payload.get("message_id") or classification_doc.id)
                classifications[message_id] = payload

            for plan_doc in account_doc.collection("action_plans").limit(limit).stream():
                payload = plan_doc.to_dict() or {}
                message_id = str(payload.get("message_id") or plan_doc.id)
                action_plans[message_id] = _flatten_plans(payload)

        reports = [
            run_doc.to_dict() or {}
            for run_doc in self.client.collection("runs").limit(limit).stream()
        ]
        return ContextData(
            emails=emails[:limit],
            classifications=classifications,
            action_plans=action_plans,
            reports=reports,
        )

    def _account_documents(self, account_ids: list[str] | None):
        if account_ids:
            return [self.client.collection("accounts").document(account_id) for account_id in account_ids]
        return list(self.client.collection("accounts").stream())


def _flatten_plans(payload: dict[str, Any]) -> list[dict[str, Any]]:
    plans = payload.get("plans")
    if isinstance(plans, dict):
        return [plan for plan in plans.values() if isinstance(plan, dict)]
    return []


def _report_intersects_accounts(report: dict[str, Any], allowed: set[str]) -> bool:
    accounts = report.get("accounts")
    if not isinstance(accounts, list):
        return True
    return any(account.get("id") in allowed for account in accounts if isinstance(account, dict))
