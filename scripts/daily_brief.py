from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [path for path in sys.path if Path(path or ".").resolve() != SCRIPT_DIR]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.context import ContextEngine, FirestoreContextRepository
from app.daily_brief import (
    DailyBriefBuilder,
    DailyBriefJsonRenderer,
    DailyBriefTextRenderer,
    FirestoreDailyBriefRepository,
)


def main() -> int:
    return main_with_args(None)


def main_with_args(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description="Daily Brief deterministico do Assistente Pessoal.")
    parser.add_argument("--project-id", default="agenda-pessoal-projeto")
    parser.add_argument("--account-id", action="append")
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--max-items-per-section", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--latest", action="store_true")
    args = parser.parse_args(argv)

    repository = FirestoreDailyBriefRepository(args.project_id)
    if args.latest:
        brief = repository.latest()
        if brief is None:
            print("Nenhum Daily Brief persistido encontrado.")
            return 1
    else:
        context_repository = FirestoreContextRepository(project_id=args.project_id)
        snapshot = ContextEngine(context_repository).build_snapshot(account_ids=args.account_id)
        brief = DailyBriefBuilder(max_items_per_section=args.max_items_per_section).build(
            snapshot,
            account_ids=args.account_id,
            timezone_name=args.timezone,
            audit_status="unknown",
        )
        should_persist = args.persist and not args.no_persist
        if should_persist:
            repository.save(brief)

    output = DailyBriefJsonRenderer().render(brief) if args.json else DailyBriefTextRenderer(max_items_per_section=args.max_items_per_section).render(brief)
    print(output)
    return 1 if brief.status == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
