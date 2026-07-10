from __future__ import annotations

from datetime import datetime, timezone

from app.daily_brief.models import DailyBrief
from app.daily_brief_delivery.gmail import DailyBriefDeliveryClient, NoopDailyBriefDeliveryClient
from app.daily_brief_delivery.models import DailyBriefDeliveryRecord, DeliveryPolicyResult
from app.daily_brief_delivery.policy import DailyBriefDeliveryPolicy, DeliveryPolicySettings
from app.daily_brief_delivery.renderers import DailyBriefEmailRenderer
from app.daily_brief_delivery.repository import DailyBriefDeliveryRepository


class DailyBriefDeliveryService:
    def __init__(
        self,
        *,
        repository: DailyBriefDeliveryRepository,
        policy: DailyBriefDeliveryPolicy | None = None,
        renderer: DailyBriefEmailRenderer | None = None,
        client: DailyBriefDeliveryClient | None = None,
    ) -> None:
        self.repository = repository
        self.policy = policy or DailyBriefDeliveryPolicy()
        self.renderer = renderer or DailyBriefEmailRenderer()
        self.client = client or NoopDailyBriefDeliveryClient()

    def deliver(
        self,
        brief: DailyBrief,
        *,
        account_id: str,
        recipient: str | None,
        mode: str,
        settings: DeliveryPolicySettings,
        dry_run: bool = True,
        force: bool = False,
        now: datetime | None = None,
    ) -> DailyBriefDeliveryRecord:
        if mode == "disabled" or not settings.enabled:
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient=recipient or "",
                mode="disabled",
                policy=DeliveryPolicyResult("BLOCK", "delivery disabled", "disabled"),
                status="skipped",
                idempotency_key=f"daily-brief:disabled:{brief.brief_id}:{account_id}",
            )
        if not recipient:
            policy = self.policy.evaluate(brief, settings=settings, recipient=recipient, mode=mode, now=now)
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient="",
                mode=mode,
                policy=policy,
                status="blocked",
                idempotency_key=f"daily-brief:no-recipient:{brief.brief_id}:{account_id}:{mode}",
            )

        message = self.renderer.render(brief, account_id=account_id, recipient=recipient, mode=mode)
        existing = self.repository.find_by_idempotency_key(message.idempotency_key)
        policy = self.policy.evaluate(
            brief,
            settings=settings,
            recipient=recipient,
            mode=mode,
            existing_record=existing,
            force=force,
            now=now,
        )

        if existing and not force:
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient=recipient or "",
                mode=mode,
                policy=policy,
                status="skipped",
                idempotency_key=message.idempotency_key,
                metadata={"existing_delivery_id": existing.delivery_id},
            )
        if policy.decision in {"BLOCK", "REVIEW"}:
            status = "blocked" if policy.decision == "BLOCK" else "skipped"
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient=recipient or "",
                mode=mode,
                policy=policy,
                status=status,
                idempotency_key=message.idempotency_key,
            )
        if dry_run:
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient=recipient or "",
                mode=mode,
                policy=policy,
                status="skipped",
                idempotency_key=message.idempotency_key,
                metadata={"dry_run": True},
            )
        try:
            if policy.decision == "ALLOW_DRAFT":
                response = self.client.create_draft(message)
                return self._record(
                    brief=brief,
                    account_id=account_id,
                    recipient=recipient or "",
                    mode=mode,
                    policy=policy,
                    status="draft_created",
                    idempotency_key=message.idempotency_key,
                    gmail_draft_id=response.get("id"),
                )
            response = self.client.send_message(message)
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient=recipient or "",
                mode=mode,
                policy=policy,
                status="sent",
                idempotency_key=message.idempotency_key,
                gmail_message_id=response.get("id"),
            )
        except Exception as exc:  # pragma: no cover - defensive audit path
            return self._record(
                brief=brief,
                account_id=account_id,
                recipient=recipient or "",
                mode=mode,
                policy=policy,
                status="failed",
                idempotency_key=message.idempotency_key,
                error=str(exc),
            )

    def _record(
        self,
        *,
        brief: DailyBrief,
        account_id: str,
        recipient: str,
        mode: str,
        policy: DeliveryPolicyResult,
        status: str,
        idempotency_key: str,
        gmail_draft_id: str | None = None,
        gmail_message_id: str | None = None,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> DailyBriefDeliveryRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = DailyBriefDeliveryRecord(
            delivery_id=f"delivery:{idempotency_key}",
            brief_id=brief.brief_id,
            account_id=account_id,
            recipient=recipient,
            mode=mode,
            policy_decision=policy.decision,
            policy_reason=policy.reason,
            status=status,
            idempotency_key=idempotency_key,
            gmail_draft_id=gmail_draft_id,
            gmail_message_id=gmail_message_id,
            error=error,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        self.repository.save(record)
        return record
