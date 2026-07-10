from __future__ import annotations

import argparse
import json

from app.communication import SubscriptionDoubleCheck
from app.context import ContextEngine
from app.context.store import FirestoreContextRepository


def main() -> int:
    return main_with_args(None)


def main_with_args(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria somente leitura do Assistente Pessoal.")
    parser.add_argument("--project-id", default="agenda-pessoal-projeto")
    parser.add_argument("--account-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repository = FirestoreContextRepository(project_id=args.project_id)
    account_ids = [args.account_id] if args.account_id else None
    data = repository.load_context_data(account_ids=account_ids)
    snapshot = ContextEngine(repository).build_snapshot(account_ids=account_ids).to_dict()
    action_plans = [plan for plans in data.action_plans.values() for plan in plans]
    discrepancies = SubscriptionDoubleCheck().inspect(
        emails=data.emails,
        subscriptions=data.subscriptions,
        action_plans=action_plans,
        context_snapshot=snapshot,
    )
    payload = {
        "status": "ok" if not discrepancies else "warning",
        "read_only": True,
        "discrepancies_count": len(discrepancies),
        "discrepancies": [item.to_dict() for item in discrepancies],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={payload['status']}")
        print("read_only=true")
        print(f"discrepancies_count={payload['discrepancies_count']}")
        for discrepancy in discrepancies:
            print(f"[{discrepancy.severity}] {discrepancy.type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
