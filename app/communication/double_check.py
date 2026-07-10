from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SubscriptionDiscrepancy:
    type: str
    severity: str
    account_id: str | None = None
    subscription_id: str | None = None
    message_id: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SubscriptionDoubleCheck:
    def inspect(
        self,
        *,
        emails: list[dict[str, Any]],
        subscriptions: list[dict[str, Any]],
        action_plans: list[dict[str, Any]],
        context_snapshot: dict[str, Any] | None = None,
    ) -> list[SubscriptionDiscrepancy]:
        discrepancies: list[SubscriptionDiscrepancy] = []
        subscription_by_id = {item.get("subscription_id"): item for item in subscriptions}
        keys_seen: set[tuple[Any, Any, Any]] = set()

        for email in emails:
            headers = {str(key).lower(): value for key, value in (email.get("raw_headers") or {}).items()}
            if any(headers.get(header) for header in ("list-unsubscribe", "list-id", "list-post")):
                if not _email_has_subscription(email, subscriptions):
                    discrepancies.append(
                        SubscriptionDiscrepancy(
                            type="subscription_headers_without_entity",
                            severity="warning",
                            account_id=email.get("account_id"),
                            message_id=email.get("id"),
                        )
                    )

        for subscription in subscriptions:
            identity = (
                subscription.get("account_id"),
                subscription.get("provider"),
                subscription.get("list_id") or subscription.get("sender_domain") or subscription.get("sender"),
            )
            if identity in keys_seen:
                discrepancies.append(
                    SubscriptionDiscrepancy(
                        type="duplicate_subscription_entity",
                        severity="error",
                        account_id=subscription.get("account_id"),
                        subscription_id=subscription.get("subscription_id"),
                    )
                )
            keys_seen.add(identity)
            if not subscription.get("schema_version"):
                discrepancies.append(
                    SubscriptionDiscrepancy(
                        type="subscription_missing_schema_version",
                        severity="warning",
                        account_id=subscription.get("account_id"),
                        subscription_id=subscription.get("subscription_id"),
                    )
                )
            if int(subscription.get("message_count") or 0) <= 0:
                discrepancies.append(
                    SubscriptionDiscrepancy(
                        type="inconsistent_message_count",
                        severity="error",
                        account_id=subscription.get("account_id"),
                        subscription_id=subscription.get("subscription_id"),
                    )
                )

        for plan in action_plans:
            if plan.get("type") != "unsubscribe_subscription":
                continue
            payload = plan.get("payload") or {}
            subscription_id = payload.get("subscription_id")
            subscription = subscription_by_id.get(subscription_id)
            if subscription is None:
                discrepancies.append(
                    SubscriptionDiscrepancy(type="action_plan_without_subscription", severity="error", subscription_id=subscription_id)
                )
            if payload.get("approval_required") is not True:
                discrepancies.append(
                    SubscriptionDiscrepancy(type="action_plan_without_required_approval", severity="error", subscription_id=subscription_id)
                )
            if payload.get("execution_enabled") is not False:
                discrepancies.append(
                    SubscriptionDiscrepancy(type="action_plan_execution_enabled", severity="error", subscription_id=subscription_id)
                )
            if subscription and subscription.get("latest_security_risk_level") in {"high", "critical"} and payload.get("execution_enabled") is not False:
                discrepancies.append(
                    SubscriptionDiscrepancy(type="high_risk_subscription_executable", severity="critical", subscription_id=subscription_id)
                )
            if subscription and subscription.get("status") == "approved":
                discrepancies.append(
                    SubscriptionDiscrepancy(type="subscription_approved_without_executor", severity="error", subscription_id=subscription_id)
                )

        if context_snapshot is not None:
            expected_total = len(subscriptions)
            actual_total = int(context_snapshot.get("subscriptions_total") or 0)
            if expected_total != actual_total:
                discrepancies.append(
                    SubscriptionDiscrepancy(
                        type="context_subscription_count_mismatch",
                        severity="warning",
                        evidence={"expected": expected_total, "actual": actual_total},
                    )
                )
        return discrepancies


def _email_has_subscription(email: dict[str, Any], subscriptions: list[dict[str, Any]]) -> bool:
    account_id = email.get("account_id")
    provider = email.get("provider")
    sender = str(email.get("sender") or "").lower()
    headers = {str(key).lower(): value for key, value in (email.get("raw_headers") or {}).items()}
    list_id = headers.get("list-id")
    return any(
        subscription.get("account_id") == account_id
        and subscription.get("provider") == provider
        and (
            (list_id and str(subscription.get("list_id") or "") in str(list_id))
            or str(subscription.get("sender") or "").lower() in sender
        )
        for subscription in subscriptions
    )
