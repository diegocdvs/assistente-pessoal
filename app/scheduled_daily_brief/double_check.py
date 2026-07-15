from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.scheduled_daily_brief.models import ScheduledDailyBriefRun


@dataclass(frozen=True)
class ScheduledDailyBriefFinding:
    type: str
    severity: str
    message: str

    def to_dict(self) -> dict:
        return {"type": self.type, "severity": self.severity, "message": self.message}


class ScheduledDailyBriefDoubleCheck:
    def inspect(
        self,
        runs: list[ScheduledDailyBriefRun],
        *,
        delivery_ids: set[str] | None = None,
        scheduler_active: bool = False,
        schedule_enabled: bool = False,
        send_mode: bool = False,
        allowlist_configured: bool = False,
        now: datetime | None = None,
    ) -> list[ScheduledDailyBriefFinding]:
        now = now or datetime.now(timezone.utc)
        delivery_ids = delivery_ids or set()
        findings: list[ScheduledDailyBriefFinding] = []
        seen_keys: set[str] = set()
        confirmed_by_logical: set[tuple[str, str, str, str]] = set()
        for run in runs:
            if not run.schema_version:
                findings.append(ScheduledDailyBriefFinding("scheduled_run_missing_schema_version", "error", run.run_id))
            if run.idempotency_key in seen_keys:
                findings.append(ScheduledDailyBriefFinding("duplicate_scheduled_idempotency_key", "critical", run.idempotency_key))
            seen_keys.add(run.idempotency_key)
            if run.status in {"draft_created", "delivered"} and run.delivery_id not in delivery_ids:
                findings.append(ScheduledDailyBriefFinding("scheduled_run_without_delivery_audit", "critical", run.run_id))
            if run.status == "running" and _is_old(run.started_at, now):
                findings.append(ScheduledDailyBriefFinding("scheduled_run_stale_running", "warning", run.run_id))
            if run.error_code == "delivery_uncertain":
                findings.append(ScheduledDailyBriefFinding("scheduled_delivery_uncertain_requires_review", "critical", run.run_id))
            if run.status in {"draft_created", "delivered"}:
                key = (run.schedule_date, run.account_scope, run.recipient_hash, run.delivery_mode)
                if key in confirmed_by_logical:
                    findings.append(ScheduledDailyBriefFinding("duplicate_confirmed_scheduled_delivery", "critical", run.run_id))
                confirmed_by_logical.add(key)
        if scheduler_active and not schedule_enabled:
            findings.append(ScheduledDailyBriefFinding("scheduler_active_with_feature_disabled", "warning", "Cloud Scheduler ativo com flag desligada."))
        if send_mode and not allowlist_configured:
            findings.append(ScheduledDailyBriefFinding("scheduled_send_without_allowlist", "critical", "Modo send sem allowlist."))
        return findings


def _is_old(started_at: str, now: datetime, minutes: int = 120) -> bool:
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    return now - started > timedelta(minutes=minutes)
