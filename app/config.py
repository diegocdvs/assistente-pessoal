from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_id: str
    region: str = "southamerica-east1"
    dry_run: bool = True
    max_emails_per_provider: int = 25
    accounts_config_path: str = "config/accounts.yaml"


def load_settings() -> Settings:
    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError("PROJECT_ID nao definido.")

    return Settings(
        project_id=project_id,
        region=os.environ.get("REGION", "southamerica-east1"),
        dry_run=os.environ.get("DRY_RUN", "true").lower() in {"1", "true", "yes", "y"},
        max_emails_per_provider=int(os.environ.get("MAX_EMAILS_PER_PROVIDER", "25")),
        accounts_config_path=os.environ.get("ACCOUNTS_CONFIG_PATH", str(Path("config") / "accounts.yaml")),
    )
