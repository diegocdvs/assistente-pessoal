from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [path for path in sys.path if Path(path or ".").resolve() != SCRIPT_DIR]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import DailyBriefDeliverySettings
from app.context import ContextEngine, FirestoreContextRepository
from app.daily_brief import DailyBriefBuilder, FirestoreDailyBriefRepository
from app.daily_brief_delivery import (
    GMAIL_DRAFT_SCOPE,
    GMAIL_SEND_SCOPE,
    DailyBriefDeliveryService,
    FirestoreDailyBriefDeliveryRepository,
    GmailDailyBriefDeliveryClient,
    NoopDailyBriefDeliveryClient,
)
from app.scheduled_daily_brief import (
    FirestoreScheduledBriefRepository,
    ScheduledDailyBriefRetryPolicy,
    ScheduledDailyBriefService,
    ScheduledDailyBriefSettings,
)


def main() -> int:
    return main_with_args(None)


def main_with_args(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description="Execucao agendada segura do Daily Brief.")
    parser.add_argument("--project-id", default=os.environ.get("PROJECT_ID", "agenda-pessoal-projeto"))
    parser.add_argument("--date")
    parser.add_argument("--timezone")
    parser.add_argument("--account-scope")
    parser.add_argument("--mode", choices=["disabled", "draft", "send"])
    parser.add_argument("--recipient")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--trigger", choices=["scheduler", "manual", "recovery", "test"], default="manual")
    parser.add_argument("--show-last-run", action="store_true")
    parser.add_argument("--list-recent", action="store_true")
    args = parser.parse_args(argv)

    run_repository = FirestoreScheduledBriefRepository(args.project_id)
    if args.show_last_run or args.list_recent:
        runs = run_repository.list_recent(limit=10 if args.list_recent else 1)
        payload = {"runs": [run.to_dict() for run in runs]}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for run in runs:
                print(f"{run.schedule_date} {run.delivery_mode} {run.status} {run.recipient_hash} {run.error_code or ''}".strip())
        return 0

    schedule_settings = _schedule_settings_from_env(args)
    delivery_settings = _delivery_settings_from_env(args, schedule_settings)
    effective_mode = args.mode or schedule_settings.mode
    client = NoopDailyBriefDeliveryClient() if args.dry_run or effective_mode == "disabled" else GmailDailyBriefDeliveryClient(
        project_id=args.project_id,
        secret_prefix=delivery_settings.secret_prefix,
        scopes=[GMAIL_SEND_SCOPE] if effective_mode == "send" else [GMAIL_DRAFT_SCOPE],
    )
    delivery_service = DailyBriefDeliveryService(
        repository=FirestoreDailyBriefDeliveryRepository(args.project_id),
        client=client,
    )
    service = ScheduledDailyBriefService(
        context_engine=ContextEngine(FirestoreContextRepository(project_id=args.project_id)),
        brief_builder=DailyBriefBuilder(),
        brief_repository=FirestoreDailyBriefRepository(args.project_id),
        delivery_service=delivery_service,
        run_repository=run_repository,
        retry_policy=ScheduledDailyBriefRetryPolicy(max_attempts=schedule_settings.max_attempts),
    )
    result = service.run(
        settings=schedule_settings,
        delivery_settings=delivery_settings,
        schedule_date=args.date,
        account_scope=args.account_scope,
        mode=args.mode,
        recipient=args.recipient,
        trigger=args.trigger,
        force=args.force,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        run = result.run
        print(f"scheduled_daily_brief: {run.status}")
        print(f"- date: {run.schedule_date}")
        print(f"- mode: {run.delivery_mode}")
        print(f"- trigger: {run.trigger}")
        print(f"- recipient: {run.recipient_hash}")
        print(f"- idempotency_key: {run.idempotency_key[:12]}...{run.idempotency_key[-6:]}")
        if run.delivery_id:
            print(f"- delivery_id: {run.delivery_id}")
        if run.error_code:
            print(f"- error_code: {run.error_code}")
            print(f"- error_summary: {run.error_summary}")
    return result.exit_code


def _schedule_settings_from_env(args: argparse.Namespace) -> ScheduledDailyBriefSettings:
    recipients = tuple(
        item.strip()
        for item in os.environ.get("DAILY_BRIEF_SCHEDULE_RECIPIENTS", "").split(",")
        if item.strip()
    )
    settings = ScheduledDailyBriefSettings(
        enabled=_env_bool("DAILY_BRIEF_SCHEDULE_ENABLED", False),
        schedule_time=os.environ.get("DAILY_BRIEF_SCHEDULE_TIME", "07:30"),
        timezone=args.timezone or os.environ.get("DAILY_BRIEF_SCHEDULE_TIMEZONE", "America/Sao_Paulo"),
        mode=args.mode or os.environ.get("DAILY_BRIEF_SCHEDULE_MODE", "draft"),
        account_scope=args.account_scope or os.environ.get("DAILY_BRIEF_SCHEDULE_ACCOUNT_SCOPE", "all"),
        recipients=((args.recipient,) if args.recipient else recipients),
        max_attempts=int(os.environ.get("DAILY_BRIEF_SCHEDULE_MAX_ATTEMPTS", "3")),
        retry_delay_seconds=int(os.environ.get("DAILY_BRIEF_SCHEDULE_RETRY_DELAY_SECONDS", "60")),
        lookback_hours=int(os.environ.get("DAILY_BRIEF_SCHEDULE_LOOKBACK_HOURS", "24")),
    )
    settings.validate()
    return settings


def _delivery_settings_from_env(args: argparse.Namespace, schedule: ScheduledDailyBriefSettings) -> DailyBriefDeliverySettings:
    recipients = tuple(
        item.strip()
        for item in os.environ.get("DAILY_BRIEF_DELIVERY_RECIPIENTS", "").split(",")
        if item.strip()
    )
    if args.recipient and args.recipient not in recipients:
        recipients = (*recipients, args.recipient)
    settings = DailyBriefDeliverySettings(
        enabled=_env_bool("DAILY_BRIEF_DELIVERY_ENABLED", False) or schedule.enabled,
        mode=args.mode or os.environ.get("DAILY_BRIEF_DELIVERY_MODE", schedule.mode),
        recipients=recipients or schedule.recipients,
        allow_send=_env_bool("DAILY_BRIEF_DELIVERY_ALLOW_SEND", False),
        start_hour=int(os.environ.get("DAILY_BRIEF_DELIVERY_START_HOUR", "0")),
        end_hour=int(os.environ.get("DAILY_BRIEF_DELIVERY_END_HOUR", "24")),
        timezone=schedule.timezone,
        sender_account_id=os.environ.get("DAILY_BRIEF_DELIVERY_SENDER_ACCOUNT_ID", "pessoal_google"),
        secret_prefix=os.environ.get("DAILY_BRIEF_DELIVERY_SECRET_PREFIX", "google-pessoal"),
        force=False,
    )
    settings.validate()
    return settings


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
