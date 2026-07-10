"""Communication management capabilities."""

from app.communication.aggregator import SubscriptionAggregator
from app.communication.double_check import SubscriptionDiscrepancy, SubscriptionDoubleCheck
from app.communication.manager import CommunicationManager
from app.communication.models import (
    RecommendationResult,
    SubscriptionApproval,
    SubscriptionCandidate,
    SubscriptionDetectionResult,
    SubscriptionEntity,
    SubscriptionStatus,
    UnsubscribeMethod,
)
from app.communication.recommendations import SubscriptionRecommendationEngine
from app.communication.repository import FirestoreSubscriptionRepository, InMemorySubscriptionRepository
from app.communication.rfc_parser import parse_unsubscribe_methods
from app.communication.subscriptions import SubscriptionDetector

__all__ = [
    "CommunicationManager",
    "FirestoreSubscriptionRepository",
    "InMemorySubscriptionRepository",
    "RecommendationResult",
    "SubscriptionAggregator",
    "SubscriptionApproval",
    "SubscriptionCandidate",
    "SubscriptionDetectionResult",
    "SubscriptionDetector",
    "SubscriptionDiscrepancy",
    "SubscriptionDoubleCheck",
    "SubscriptionEntity",
    "SubscriptionRecommendationEngine",
    "SubscriptionStatus",
    "UnsubscribeMethod",
    "parse_unsubscribe_methods",
]
