from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from app.calendar import DailyAgendaBuilder
from app.context import ContextEngine, FirestoreContextRepository


def main() -> int:
    return main_with_args(None)


def main_with_args(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description="CLI read-only de Google Calendar.")
    parser.add_argument("--project-id", default="agenda-pessoal-projeto")
    parser.add_argument("--account-id")
    parser.add_argument("--calendar-id")
    parser.add_argument("--today", action="store_true")
    parser.add_argument("--tomorrow", action="store_true")
    parser.add_argument("--upcoming", action="store_true")
    parser.add_argument("--conflicts", action="store_true")
    parser.add_argument("--free-windows", action="store_true")
    parser.add_argument("--daily-agenda", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    context_repository = FirestoreContextRepository(project_id=args.project_id)
    snapshot = ContextEngine(context_repository).build_snapshot(account_ids=[args.account_id] if args.account_id else None)
    payload = snapshot.to_dict()
    if args.calendar_id:
        payload["calendar_events_today"] = [event for event in payload["calendar_events_today"] if event.get("calendar_id") == args.calendar_id]
        payload["calendar_events_tomorrow"] = [event for event in payload["calendar_events_tomorrow"] if event.get("calendar_id") == args.calendar_id]

    response = {
        "dry_run": True,
        "read_only": True,
        "calendar_events_today": payload["calendar_events_today"],
        "calendar_events_tomorrow": payload["calendar_events_tomorrow"],
        "next_event": payload["next_event"],
        "calendar_conflicts": payload["calendar_conflicts"],
        "free_windows_today": payload["free_windows_today"],
        "calendar_security_warnings": payload["calendar_security_warnings"],
    }
    if args.daily_agenda:
        response["daily_agenda"] = _agenda_from_snapshot(payload)

    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"read_only=true dry_run=true")
        print(f"eventos_hoje={len(response['calendar_events_today'])}")
        print(f"eventos_amanha={len(response['calendar_events_tomorrow'])}")
        print(f"conflitos={len(response['calendar_conflicts'])}")
        print(f"janelas_livres={len(response['free_windows_today'])}")
        if response["next_event"]:
            print(f"proximo={response['next_event'].get('start_at')} {response['next_event'].get('title')}")
    return 0


def _agenda_from_snapshot(snapshot: dict) -> dict:
    agenda = DailyAgendaBuilder().build(
        day=datetime.now(timezone.utc).date(),
        timezone="America/Sao_Paulo",
        events=[],
        critical_emails=snapshot.get("emails_critical", []),
        followups=snapshot.get("followups", []),
        action_plans=snapshot.get("action_plans", []),
        subscriptions_waiting_approval=snapshot.get("subscriptions_waiting_approval", 0),
        security_warnings=snapshot.get("calendar_security_warnings", []) + snapshot.get("warning_items", []),
        top_priorities=snapshot.get("top_priorities", []),
        double_check_status="unknown",
    )
    payload = agenda.to_dict()
    payload["events_today"] = snapshot.get("calendar_events_today", [])
    payload["next_event"] = snapshot.get("next_event")
    payload["conflicts"] = snapshot.get("calendar_conflicts", [])
    payload["free_windows"] = snapshot.get("free_windows_today", [])
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
