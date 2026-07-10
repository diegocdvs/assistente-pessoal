from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.communication.aggregator import SubscriptionAggregator
from app.communication.models import RecommendationResult, SubscriptionEntity, SubscriptionStatus
from app.communication.recommendations import SubscriptionRecommendationEngine
from app.communication.repository import InMemorySubscriptionRepository, SubscriptionRepository
from app.core.models import ActionPlan, EmailEntity
from app.security import SecurityDecision
from app.security.models import SecurityAssessment

logger = logging.getLogger(__name__)


class CommunicationManager:
    def __init__(
        self,
        *,
        repository: SubscriptionRepository | None = None,
        aggregator: SubscriptionAggregator | None = None,
        recommendation_engine: SubscriptionRecommendationEngine | None = None,
        dry_run: bool = True,
    ) -> None:
        self.repository = repository or InMemorySubscriptionRepository()
        self.aggregator = aggregator or SubscriptionAggregator()
        self.recommendation_engine = recommendation_engine or SubscriptionRecommendationEngine()
        self.dry_run = dry_run

    def process_emails(
        self,
        emails: list[EmailEntity | dict[str, Any]],
        *,
        classifications: dict[str, dict[str, Any]] | None = None,
        security_assessments: dict[str, SecurityAssessment] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        started = datetime.now(timezone.utc)
        existing = self.repository.list_subscriptions()
        aggregated = self.aggregator.aggregate(
            emails,
            classifications=classifications,
            security_assessments=security_assessments,
            existing=existing,
        )
        persisted: list[SubscriptionEntity] = []
        action_plans: list[ActionPlan] = []
        blocked_count = 0

        for subscription in aggregated:
            recommendation = self.recommendation_engine.evaluate(subscription)
            enriched = self._apply_recommendation(subscription, recommendation)
            persisted_subscription = self.repository.upsert_subscription(enriched)
            persisted.append(persisted_subscription)
            plan = self.plan_unsubscribe(persisted_subscription, recommendation)
            if plan:
                action_plans.append(plan)
            if recommendation.blocked_by_security:
                blocked_count += 1

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        logger.info(
            "communication_manager",
            extra={
                "run_id": run_id,
                "stage": "subscription_management",
                "detected_count": len(aggregated),
                "aggregated_count": len(persisted),
                "recommended_count": len([item for item in persisted if item.status == SubscriptionStatus.UNSUBSCRIBE_RECOMMENDED.value]),
                "blocked_count": blocked_count,
                "action_plans_created": len(action_plans),
                "duration": duration,
                "status": "ok",
            },
        )
        return {
            "subscriptions": persisted,
            "action_plans": action_plans,
            "summary": self.summary(persisted),
        }

    def plan_unsubscribe(
        self,
        subscription: SubscriptionEntity,
        recommendation: RecommendationResult | None = None,
    ) -> ActionPlan | None:
        recommendation = recommendation or self.recommendation_engine.evaluate(subscription)
        if not subscription.unsubscribe_supported:
            return None
        if not recommendation.recommended and not recommendation.blocked_by_security:
            return None

        method_payload = _preferred_method_payload(subscription)
        if method_payload is None:
            return None
        blocked = recommendation.blocked_by_security or _security_policy_blocks(subscription.audit_metadata)
        return ActionPlan(
            type="unsubscribe_subscription",
            reason="Cancelamento de subscription recomendado para aprovacao manual."
            if not blocked
            else "Subscription exige revisao manual por risco de seguranca.",
            dry_run=True,
            status=SubscriptionStatus.WAITING_APPROVAL.value,
            payload={
                "subscription_id": subscription.subscription_id,
                "account_id": subscription.account_id,
                "provider": subscription.provider,
                "method": method_payload.get("method"),
                "target": method_payload.get("redacted_target"),
                "recommendation_score": recommendation.recommendation_score,
                "recommendation_reasons": list(recommendation.recommendation_reasons),
                "security_risk_level": subscription.latest_security_risk_level,
                "security_risk_score": subscription.latest_security_risk_score,
                "approval_required": True,
                "execution_enabled": False,
                "idempotency_key": f"unsubscribe:{subscription.account_id}:{subscription.subscription_id}",
                "dry_run": True,
                "audit_metadata": {
                    "source": "communication_manager",
                    "blocked_by_security": blocked,
                },
            },
            id=f"{subscription.account_id}:{subscription.subscription_id}:unsubscribe_subscription".replace("/", "_"),
            source="communication_manager",
            audit_metadata={
                "subscription_id": subscription.subscription_id,
                "approval_required": True,
                "execution_enabled": False,
                "dry_run": True,
            },
        )

    def list_subscriptions(self, *, account_id: str | None = None, status: str | None = None) -> list[SubscriptionEntity]:
        return self.repository.list_subscriptions(account_id=account_id, status=status)

    def mark_favorite(self, account_id: str, subscription_id: str) -> SubscriptionEntity:
        return self._set_status(account_id, subscription_id, SubscriptionStatus.FAVORITE.value)

    def mark_ignored(self, account_id: str, subscription_id: str) -> SubscriptionEntity:
        return self._set_status(account_id, subscription_id, SubscriptionStatus.IGNORED.value)

    def revoke_recommendation(self, account_id: str, subscription_id: str) -> SubscriptionEntity:
        return self._set_status(account_id, subscription_id, SubscriptionStatus.ACTIVE.value)

    def summary(self, subscriptions: list[SubscriptionEntity] | None = None) -> dict[str, Any]:
        subscriptions = subscriptions or self.repository.list_subscriptions()
        return {
            "subscriptions_total": len(subscriptions),
            "subscriptions_active": len([item for item in subscriptions if item.status == SubscriptionStatus.ACTIVE.value]),
            "subscriptions_new": len([item for item in subscriptions if item.status == SubscriptionStatus.DETECTED.value]),
            "subscriptions_recommended_for_unsubscribe": len(
                [item for item in subscriptions if item.status == SubscriptionStatus.UNSUBSCRIBE_RECOMMENDED.value]
            ),
            "subscriptions_waiting_approval": len(
                [item for item in subscriptions if item.status == SubscriptionStatus.WAITING_APPROVAL.value]
            ),
            "subscriptions_blocked_by_security": len(
                [item for item in subscriptions if item.latest_security_risk_level in {"high", "critical"}]
            ),
            "top_subscription_candidates": [
                item.to_dict()
                for item in sorted(subscriptions, key=lambda value: value.recommendation_score, reverse=True)[:5]
            ],
        }

    def _apply_recommendation(
        self,
        subscription: SubscriptionEntity,
        recommendation: RecommendationResult,
    ) -> SubscriptionEntity:
        status = subscription.status
        if recommendation.blocked_by_security:
            status = SubscriptionStatus.QUARANTINED.value
        elif recommendation.recommended:
            status = SubscriptionStatus.UNSUBSCRIBE_RECOMMENDED.value
        elif status == SubscriptionStatus.DETECTED.value and subscription.message_count > 1:
            status = SubscriptionStatus.ACTIVE.value
        return replace(
            subscription,
            status=status,
            recommendation_score=recommendation.recommendation_score,
            recommendation_reasons=list(recommendation.recommendation_reasons),
        )

    def _set_status(self, account_id: str, subscription_id: str, status: str) -> SubscriptionEntity:
        subscription = self.repository.get_subscription(account_id, subscription_id)
        if subscription is None:
            raise KeyError(subscription_id)
        updated = replace(subscription, status=status, updated_at=datetime.now(timezone.utc).isoformat())
        return self.repository.upsert_subscription(updated)


def _preferred_method_payload(subscription: SubscriptionEntity) -> dict[str, Any] | None:
    if not subscription.unsubscribe_methods:
        return None
    for method in subscription.unsubscribe_methods:
        if method.get("one_click") and method.get("method") == "https":
            return method
    for method in subscription.unsubscribe_methods:
        if method.get("method") == "https":
            return method
    return subscription.unsubscribe_methods[0]


def _security_policy_blocks(audit_metadata: dict[str, Any]) -> bool:
    latest_detection = audit_metadata.get("latest_detection")
    decision = audit_metadata.get("policy_decision")
    return decision in {SecurityDecision.BLOCK.value, SecurityDecision.QUARANTINE.value} or (
        isinstance(latest_detection, dict) and latest_detection.get("risk_recommendation") == "manual_review_required"
    )
