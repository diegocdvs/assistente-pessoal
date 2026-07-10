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


def main() -> int:
    return main_with_args(None)


def main_with_args(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description="Entrega segura do Daily Brief por Gmail.")
    parser.add_argument("--project-id", default=os.environ.get("PROJECT_ID", "agenda-pessoal-projeto"))
    parser.add_argument("--account-id", action="append")
    parser.add_argument("--sender-account-id")
    parser.add_argument("--secret-prefix")
    parser.add_argument("--recipient")
    parser.add_argument("--mode", choices=["disabled", "draft", "send"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--use-last-brief", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    settings = _settings_from_env(args)
    brief_repository = FirestoreDailyBriefRepository(args.project_id)
    if args.use_last_brief:
        brief = brief_repository.latest()
        if brief is None:
            print("Nenhum Daily Brief persistido encontrado.")
            return 1
    else:
        context_repository = FirestoreContextRepository(project_id=args.project_id)
        snapshot = ContextEngine(context_repository).build_snapshot(account_ids=args.account_id)
        brief = DailyBriefBuilder().build(
            snapshot,
            account_ids=args.account_id,
            timezone_name=settings.timezone,
            audit_status="unknown",
        )
        brief_repository.save(brief)

    mode = args.mode or settings.mode
    recipient = args.recipient or (settings.recipients[0] if settings.recipients else None)
    dry_run = args.dry_run
    client = NoopDailyBriefDeliveryClient() if dry_run or mode == "disabled" else GmailDailyBriefDeliveryClient(
        project_id=args.project_id,
        secret_prefix=settings.secret_prefix,
        scopes=[GMAIL_SEND_SCOPE] if mode == "send" else [GMAIL_DRAFT_SCOPE],
    )
    record = DailyBriefDeliveryService(
        repository=FirestoreDailyBriefDeliveryRepository(args.project_id),
        client=client,
    ).deliver(
        brief,
        account_id=settings.sender_account_id,
        recipient=recipient,
        mode=mode,
        settings=settings,
        dry_run=dry_run,
        force=args.force or settings.force,
    )

    if args.json:
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Daily Brief delivery: {record.status}")
        print(f"- mode: {record.mode}")
        print(f"- policy: {record.policy_decision} ({record.policy_reason})")
        print(f"- delivery_id: {record.delivery_id}")
        if record.gmail_draft_id:
            print(f"- gmail_draft_id: {record.gmail_draft_id}")
        if record.gmail_message_id:
            print(f"- gmail_message_id: {record.gmail_message_id}")
        if record.error:
            print(f"- error: {record.error}")

    if record.status == "failed":
        return 1
    if record.status == "blocked" and record.mode != "disabled":
        return 2
    return 0


def _settings_from_env(args: argparse.Namespace) -> DailyBriefDeliverySettings:
    recipients = tuple(
        item.strip()
        for item in os.environ.get("DAILY_BRIEF_DELIVERY_RECIPIENTS", "").split(",")
        if item.strip()
    )
    settings = DailyBriefDeliverySettings(
        enabled=_env_bool("DAILY_BRIEF_DELIVERY_ENABLED", False),
        mode=args.mode or os.environ.get("DAILY_BRIEF_DELIVERY_MODE", "disabled"),
        recipients=((args.recipient,) if args.recipient else recipients),
        allow_send=_env_bool("DAILY_BRIEF_DELIVERY_ALLOW_SEND", False),
        start_hour=int(os.environ.get("DAILY_BRIEF_DELIVERY_START_HOUR", "5")),
        end_hour=int(os.environ.get("DAILY_BRIEF_DELIVERY_END_HOUR", "11")),
        timezone=os.environ.get("DAILY_BRIEF_DELIVERY_TIMEZONE", os.environ.get("DAILY_BRIEF_TIMEZONE", "America/Sao_Paulo")),
        sender_account_id=args.sender_account_id or os.environ.get("DAILY_BRIEF_DELIVERY_SENDER_ACCOUNT_ID", "pessoal_google"),
        secret_prefix=args.secret_prefix or os.environ.get("DAILY_BRIEF_DELIVERY_SECRET_PREFIX", "google-pessoal"),
        force=args.force or _env_bool("DAILY_BRIEF_DELIVERY_FORCE", False),
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
