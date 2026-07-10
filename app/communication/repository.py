from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Protocol

from google.cloud import firestore

from app.communication.models import SubscriptionApproval, SubscriptionEntity


class SubscriptionRepository(Protocol):
    def list_subscriptions(self, *, account_id: str | None = None, status: str | None = None) -> list[SubscriptionEntity]:
        pass

    def get_subscription(self, account_id: str, subscription_id: str) -> SubscriptionEntity | None:
        pass

    def upsert_subscription(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        pass

    def save_approval(self, approval: SubscriptionApproval, *, account_id: str) -> str:
        pass


class InMemorySubscriptionRepository:
    def __init__(self, subscriptions: list[SubscriptionEntity] | None = None) -> None:
        self.subscriptions = {
            (subscription.account_id, subscription.subscription_id): subscription
            for subscription in subscriptions or []
        }
        self.approvals: dict[tuple[str, str], SubscriptionApproval] = {}

    def list_subscriptions(self, *, account_id: str | None = None, status: str | None = None) -> list[SubscriptionEntity]:
        values = list(self.subscriptions.values())
        if account_id:
            values = [subscription for subscription in values if subscription.account_id == account_id]
        if status:
            values = [subscription for subscription in values if subscription.status == status]
        return sorted(values, key=lambda item: item.subscription_id)

    def get_subscription(self, account_id: str, subscription_id: str) -> SubscriptionEntity | None:
        return self.subscriptions.get((account_id, subscription_id))

    def upsert_subscription(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        key = (subscription.account_id, subscription.subscription_id)
        existing = self.subscriptions.get(key)
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            subscription = replace(
                subscription,
                first_seen_at=min(existing.first_seen_at, subscription.first_seen_at),
                message_count=max(existing.message_count, subscription.message_count),
                created_at=existing.created_at,
                updated_at=now,
            )
        self.subscriptions[key] = subscription
        return subscription

    def save_approval(self, approval: SubscriptionApproval, *, account_id: str) -> str:
        self.approvals[(account_id, approval.approval_id)] = approval
        return approval.approval_id


class FirestoreSubscriptionRepository:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def list_subscriptions(self, *, account_id: str | None = None, status: str | None = None) -> list[SubscriptionEntity]:
        documents = []
        if account_id:
            documents = list(self._subscriptions(account_id).stream())
        else:
            for account_doc in self.client.collection("accounts").stream():
                documents.extend(account_doc.reference.collection("subscriptions").stream())
        subscriptions = [
            SubscriptionEntity(**payload)
            for doc in documents
            if (payload := doc.to_dict() or {})
        ]
        if status:
            subscriptions = [subscription for subscription in subscriptions if subscription.status == status]
        return sorted(subscriptions, key=lambda item: item.subscription_id)

    def get_subscription(self, account_id: str, subscription_id: str) -> SubscriptionEntity | None:
        payload = self._subscriptions(account_id).document(_safe_document_id(subscription_id)).get().to_dict()
        return SubscriptionEntity(**payload) if payload else None

    def upsert_subscription(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        self._subscriptions(subscription.account_id).document(_safe_document_id(subscription.subscription_id)).set(
            subscription.to_dict(),
            merge=True,
        )
        return subscription

    def save_approval(self, approval: SubscriptionApproval, *, account_id: str) -> str:
        self.client.collection("accounts").document(account_id).collection("subscription_approvals").document(
            _safe_document_id(approval.approval_id)
        ).set(approval.to_dict(), merge=True)
        return approval.approval_id

    def _subscriptions(self, account_id: str):
        return self.client.collection("accounts").document(account_id).collection("subscriptions")


def _safe_document_id(value: str) -> str:
    return value.replace("/", "_")
