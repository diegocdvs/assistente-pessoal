from __future__ import annotations

from app.communication.models import RecommendationResult, SubscriptionEntity, SubscriptionStatus

BLOCKING_RISK_LEVELS = {"high", "critical"}
RECOMMENDABLE_CATEGORIES = {"promocao", "newsletter"}


class SubscriptionRecommendationEngine:
    def evaluate(self, subscription: SubscriptionEntity) -> RecommendationResult:
        score = 0
        reasons: list[str] = []
        blocked_by_security = subscription.latest_security_risk_level in BLOCKING_RISK_LEVELS

        if subscription.status == SubscriptionStatus.FAVORITE.value:
            return RecommendationResult(0, ["favorite_subscription"], False, blocked_by_security, False)
        if subscription.status == SubscriptionStatus.IGNORED.value:
            return RecommendationResult(0, ["ignored_subscription"], False, blocked_by_security, False)

        if subscription.category in RECOMMENDABLE_CATEGORIES:
            score += 25
            reasons.append(f"category:{subscription.category}")
        if subscription.message_count >= 10:
            score += 25
            reasons.append("high_accumulated_volume")
        elif subscription.message_count >= 3:
            score += 10
            reasons.append("recurring_sender")
        if subscription.estimated_frequency in {"daily", "weekly"}:
            score += 20
            reasons.append(f"frequency:{subscription.estimated_frequency}")
        if subscription.unsubscribe_supported:
            score += 20
            reasons.append("official_rfc_unsubscribe_available")
        else:
            reasons.append("no_official_unsubscribe_mechanism")
        if blocked_by_security:
            score += 15
            reasons.append(f"security_risk:{subscription.latest_security_risk_level}")

        recommended = score >= 45 and subscription.unsubscribe_supported and not blocked_by_security
        requires_review = blocked_by_security or score >= 40
        return RecommendationResult(
            recommendation_score=min(score, 100),
            recommendation_reasons=reasons,
            recommended=recommended,
            blocked_by_security=blocked_by_security,
            requires_review=requires_review,
        )
