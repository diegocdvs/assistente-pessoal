from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project_id: str
    region: str = "southamerica-east1"
    dry_run: bool = True
    max_emails_per_provider: int = 25

    google_client_secret_name: str = "google-client-secret-json"
    google_refresh_token_name: str = "google-refresh-token"
    outlook_secret_name: str = "outlook-oauth-json"
    whatsapp_secret_name: str = "whatsapp-config-json"


def load_settings() -> Settings:
    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError("PROJECT_ID não definido.")

    return Settings(
        project_id=project_id,
        region=os.environ.get("REGION", "southamerica-east1"),
        dry_run=os.environ.get("DRY_RUN", "true").lower() in {"1", "true", "yes", "y"},
        max_emails_per_provider=int(os.environ.get("MAX_EMAILS_PER_PROVIDER", "25")),
    )
