from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.context import ContextEngine
from app.daily_brief import DailyBriefBuilder
from app.daily_brief.repository import DailyBriefRepository
from app.daily_brief_delivery import DailyBriefDeliveryService
from app.daily_brief_delivery.policy import DeliveryPolicySettings
from app.scheduled_daily_brief.idempotency import build_scheduled_idempotency_key, hash_recipient, redact_key, redact_recipient
from app.scheduled_daily_brief.models import ScheduledDailyBriefResult, ScheduledDailyBriefRun, utc_now
from app.scheduled_daily_brief.repository import CONFIRMED_STATUSES, ScheduledBriefRepository
from app.scheduled_daily_brief.retry import ScheduledDailyBriefRetryPolicy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduledDailyBriefSettings:
    enabled: bool = False
    schedule_time: str = "07:30"
    timezone: str = "America/Sao_Paulo"
    mode: str = "draft"
    account_scope: str = "all"
    recipients: tuple[str, ...] = ()
    max_attempts: int = 3
    retry_delay_seconds: int = 60
    lookback_hours: int = 24

    def validate(self) -> None:
        ZoneInfo(self.timezone)
        _parse_schedule_time(self.schedule_time)
        if self.mode not in {"disabled", "draft", "send"}:
            raise ValueError("DAILY_BRIEF_SCHEDULE_MODE deve ser disabled, draft ou send.")
        if self.max_attempts < 1 or self.max_attempts > 5:
            raise ValueError("DAILY_BRIEF_SCHEDULE_MAX_ATTEMPTS deve estar entre 1 e 5.")
        if self.retry_delay_seconds < 0 or self.retry_delay_seconds > 3600:
            raise ValueError("DAILY_BRIEF_SCHEDULE_RETRY_DELAY_SECONDS deve estar entre 0 e 3600.")
        if self.lookback_hours < 1 or self.lookback_hours > 168:
            raise ValueError("DAILY_BRIEF_SCHEDULE_LOOKBACK_HOURS deve estar entre 1 e 168.")


class ScheduledDailyBriefService:
    def __init__(
        self,
        *,
        context_engine: ContextEngine,
        brief_builder: DailyBriefBuilder,
        brief_repository: DailyBriefRepository,
        delivery_service: DailyBriefDeliveryService,
        run_repository: ScheduledBriefRepository,
        retry_policy: ScheduledDailyBriefRetryPolicy | None = None,
    ) -> None:
        self.context_engine = context_engine
        self.brief_builder = brief_builder
        self.brief_repository = brief_repository
        self.delivery_service = delivery_service
        self.run_repository = run_repository
        self.retry_policy = retry_policy or ScheduledDailyBriefRetryPolicy()

    def run(
        self,
        *,
        settings: ScheduledDailyBriefSettings,
        delivery_settings: DeliveryPolicySettings,
        schedule_date: str | None = None,
        account_scope: str | None = None,
        mode: str | None = None,
        recipient: str | None = None,
        trigger: str = "manual",
        force: bool = False,
        dry_run: bool = True,
        now: datetime | None = None,
    ) -> ScheduledDailyBriefResult:
        started = datetime.now(timezone.utc)
        now = now or datetime.now(ZoneInfo(settings.timezone))
        settings.validate()
        effective_mode = mode or settings.mode
        effective_scope = account_scope or settings.account_scope
        effective_date = schedule_date or now.astimezone(ZoneInfo(settings.timezone)).date().isoformat()
        effective_recipient = recipient or (settings.recipients[0] if settings.recipients else "")
        idempotency_key = build_scheduled_idempotency_key(
            schedule_date=effective_date,
            timezone_name=settings.timezone,
            account_scope=effective_scope,
            delivery_mode=effective_mode,
            recipient=effective_recipient,
        )
        run = ScheduledDailyBriefRun(
            run_id=f"scheduled:{idempotency_key}",
            schedule_date=effective_date,
            timezone=settings.timezone,
            account_scope=effective_scope,
            delivery_mode=effective_mode,
            recipient_hash=hash_recipient(effective_recipient),
            idempotency_key=idempotency_key,
            status="pending",
            started_at=started.isoformat(),
            trigger=trigger,
            audit_metadata={
                "recipient": redact_recipient(effective_recipient),
                "dry_run": dry_run,
                "force": force,
            },
        )
        _log("scheduled_daily_brief_acquire", run, stage="acquire")
        acquired_run, acquired = self.run_repository.acquire(run)
        if not acquired:
            if acquired_run.status in CONFIRMED_STATUSES:
                skipped = self.run_repository.mark_skipped(
                    acquired_run,
                    reason=f"confirmed delivery already exists: {acquired_run.status}",
                )
                return ScheduledDailyBriefResult(skipped, retryable=False, exit_code=0)
            if acquired_run.status == "running":
                skipped = self.run_repository.mark_skipped(acquired_run, reason="another execution is already running")
                return ScheduledDailyBriefResult(skipped, retryable=False, exit_code=0)
            if not _can_resume(acquired_run):
                skipped = self.run_repository.mark_skipped(acquired_run, reason=f"previous status blocks resume: {acquired_run.status}")
                return ScheduledDailyBriefResult(skipped, retryable=False, exit_code=0)
            run = acquired_run

        running = self.run_repository.mark_running(run)
        if not settings.enabled or effective_mode == "disabled":
            skipped = self.run_repository.mark_skipped(running, reason="schedule disabled")
            return ScheduledDailyBriefResult(skipped, retryable=False, exit_code=0)
        if not force and not _inside_schedule_window(settings, now):
            blocked = self.run_repository.mark_blocked(running, error_code="outside_schedule_window", error_summary="outside configured schedule window")
            return ScheduledDailyBriefResult(blocked, retryable=False, exit_code=2)

        try:
            account_ids = None if effective_scope == "all" else [item.strip() for item in effective_scope.split(",") if item.strip()]
            snapshot = self.context_engine.build_snapshot(account_ids=account_ids, now=now.astimezone(timezone.utc))
            brief = self.brief_builder.build(snapshot, account_ids=account_ids, timezone_name=settings.timezone, audit_status="unknown")
            self.brief_repository.save(brief)
            delivery_record = self.delivery_service.deliver(
                brief,
                account_id=getattr(delivery_settings, "sender_account_id", "pessoal_google"),
                recipient=effective_recipient,
                mode=effective_mode,
                settings=delivery_settings,
                dry_run=dry_run,
                force=False,
                now=now,
            )
            if delivery_record.status == "draft_created":
                final = self.run_repository.mark_draft_created(running, brief_id=brief.brief_id, delivery_id=delivery_record.delivery_id)
            elif delivery_record.status == "sent":
                final = self.run_repository.mark_delivered(running, brief_id=brief.brief_id, delivery_id=delivery_record.delivery_id)
            elif delivery_record.status == "skipped":
                final = self.run_repository.mark_skipped(running.with_updates(brief_id=brief.brief_id, delivery_id=delivery_record.delivery_id), reason=delivery_record.policy_reason)
            elif delivery_record.status == "blocked":
                final = self.run_repository.mark_blocked(
                    running.with_updates(brief_id=brief.brief_id, delivery_id=delivery_record.delivery_id),
                    error_code=_policy_error_code(delivery_record.policy_reason),
                    error_summary=delivery_record.policy_reason,
                )
            else:
                code = "delivery_uncertain" if _maybe_delivery_attempted(delivery_record) else "delivery_failed"
                final = self.run_repository.mark_failed(
                    running.with_updates(brief_id=brief.brief_id, delivery_id=delivery_record.delivery_id),
                    error_code=code,
                    error_summary=delivery_record.error or "delivery failed",
                )
            _log("scheduled_daily_brief_finished", final, stage="finish")
            retry = self.retry_policy.classify(error_code=final.error_code, attempt=final.attempt, possible_delivery=final.error_code == "delivery_uncertain")
            return ScheduledDailyBriefResult(final, retryable=retry.retryable, exit_code=_exit_code(final))
        except Exception as exc:
            error_code = _classify_exception(exc)
            failed = self.run_repository.mark_failed(running, error_code=error_code, error_summary=_safe_error(str(exc)))
            retry = self.retry_policy.classify(error_code=error_code, attempt=failed.attempt)
            return ScheduledDailyBriefResult(failed, retryable=retry.retryable, exit_code=1)


def _inside_schedule_window(settings: ScheduledDailyBriefSettings, now: datetime) -> bool:
    scheduled_hour, scheduled_minute = _parse_schedule_time(settings.schedule_time)
    local = now.astimezone(ZoneInfo(settings.timezone))
    scheduled = local.replace(hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0)
    delta_seconds = abs((local - scheduled).total_seconds())
    return delta_seconds <= settings.lookback_hours * 3600


def _parse_schedule_time(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("DAILY_BRIEF_SCHEDULE_TIME deve usar formato HH:MM.")
    hour, minute = int(parts[0]), int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("DAILY_BRIEF_SCHEDULE_TIME invalido.")
    return hour, minute


def _can_resume(run: ScheduledDailyBriefRun) -> bool:
    return run.status == "failed" and run.error_code not in {"delivery_uncertain", "delivery_already_confirmed"}


def _policy_error_code(reason: str | None) -> str:
    reason = reason or ""
    if "allowlist" in reason:
        return "recipient_outside_allowlist"
    if "requires explicit allow_send" in reason:
        return "blocked_by_policy"
    if "ERROR" in reason or "high risk" in reason:
        return "security_error"
    return "blocked_by_policy"


def _maybe_delivery_attempted(delivery_record) -> bool:
    return bool(delivery_record.error and delivery_record.policy_decision in {"ALLOW_DRAFT", "ALLOW_SEND"})


def _classify_exception(exc: Exception) -> str:
    text = str(exc).lower()
    if "timeout" in text:
        return "timeout"
    if "429" in text or "rate" in text:
        return "rate_limit"
    if "503" in text or "500" in text:
        return "http_5xx"
    if "credential" in text or "secret" in text:
        return "missing_credentials"
    if "scope" in text:
        return "insufficient_oauth_scope"
    return "temporary_unavailable"


def _safe_error(value: str) -> str:
    return value.replace("\n", " ")[:240]


def _exit_code(run: ScheduledDailyBriefRun) -> int:
    if run.status in {"skipped", "draft_created", "delivered"}:
        return 0
    if run.status == "blocked":
        return 2
    return 1


def _log(event: str, run: ScheduledDailyBriefRun, *, stage: str) -> None:
    logger.info(
        json.dumps(
            {
                "event": event,
                "run_id": run.run_id,
                "idempotency_key": redact_key(run.idempotency_key),
                "schedule_date": run.schedule_date,
                "timezone": run.timezone,
                "mode": run.delivery_mode,
                "trigger": run.trigger,
                "stage": stage,
                "attempt": run.attempt,
                "status": run.status,
                "delivery_id": run.delivery_id,
                "error_code": run.error_code,
            },
            sort_keys=True,
        )
    )
