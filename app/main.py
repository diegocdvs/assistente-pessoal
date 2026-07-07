from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.config import load_settings
from app.core.daily_job import DailyJob

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = load_settings()
    logger.info("Iniciando Assistente Pessoal. dry_run=%s project=%s", settings.dry_run, settings.project_id)

    job = DailyJob(settings)
    report = job.run()

    print(json.dumps({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": settings.dry_run,
        "report": report,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
