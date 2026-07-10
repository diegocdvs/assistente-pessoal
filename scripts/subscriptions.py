from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [path for path in sys.path if Path(path or ".").resolve() != SCRIPT_DIR]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.communication import CommunicationManager, FirestoreSubscriptionRepository
from app.context.store import FirestoreContextRepository


def main() -> int:
    return main_with_args(None)


def main_with_args(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description="Operacao segura de subscriptions.")
    parser.add_argument("--project-id", default="agenda-pessoal-projeto")
    parser.add_argument("--account-id")
    parser.add_argument("--status")
    parser.add_argument("--recommended", action="store_true")
    parser.add_argument("--blocked", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--detect-persisted", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repository = FirestoreSubscriptionRepository(project_id=args.project_id)
    manager = CommunicationManager(repository=repository, dry_run=True)

    if args.detect_persisted:
        context_repository = FirestoreContextRepository(project_id=args.project_id)
        data = context_repository.load_context_data(account_ids=[args.account_id] if args.account_id else None)
        result = manager.process_emails(data.emails, classifications=data.classifications)
        subscriptions = result["subscriptions"]
    else:
        subscriptions = manager.list_subscriptions(account_id=args.account_id, status=args.status)

    if args.recommended:
        subscriptions = [item for item in subscriptions if item.status == "unsubscribe_recommended"]
    if args.blocked:
        subscriptions = [item for item in subscriptions if item.latest_security_risk_level in {"high", "critical"}]

    payload = {
        "dry_run": True,
        "unsubscribe_execution_available": False,
        "summary": manager.summary(subscriptions),
        "subscriptions": [_safe_subscription(item.to_dict()) for item in subscriptions],
    }

    if args.summary and not args.json:
        print(f"subscriptions_total={payload['summary']['subscriptions_total']}")
        print(f"recommended={payload['summary']['subscriptions_recommended_for_unsubscribe']}")
        print(f"blocked_by_security={payload['summary']['subscriptions_blocked_by_security']}")
        print("unsubscribe_execution_available=false")
        return 0

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for subscription in payload["subscriptions"]:
            print(
                "{subscription_id} account={account_id} provider={provider} "
                "status={status} score={recommendation_score} sender_domain={sender_domain}".format(**subscription)
            )
        if not payload["subscriptions"]:
            print("Nenhuma subscription encontrada.")
    return 0


def _safe_subscription(payload: dict[str, Any]) -> dict[str, Any]:
    safe = dict(payload)
    safe.pop("unsubscribe_url", None)
    safe.pop("unsubscribe_email", None)
    safe["unsubscribe_methods"] = [
        {
            "method": method.get("method"),
            "target": method.get("redacted_target", "[redacted]"),
            "one_click": method.get("one_click", False),
        }
        for method in safe.get("unsubscribe_methods", [])
        if isinstance(method, dict)
    ]
    return safe


if __name__ == "__main__":
    raise SystemExit(main())
