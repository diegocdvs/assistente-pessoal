from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.calendar.config import CalendarSettings


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class FeatureFlags:
    outlook_enabled: bool = False
    calendar_enabled: bool = False
    whatsapp_enabled: bool = False
    ai_enabled: bool = False
    auto_execution_enabled: bool = False


@dataclass(frozen=True)
class Limits:
    max_emails_per_provider: int = 25


@dataclass(frozen=True)
class Settings:
    project_id: str
    region: str = "southamerica-east1"
    dry_run: bool = True
    max_emails_per_provider: int = 25
    accounts_config_path: str = "config/accounts.yaml"
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    limits: Limits = field(default_factory=Limits)
    calendar: CalendarSettings = field(default_factory=CalendarSettings)


def load_settings() -> Settings:
    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError("PROJECT_ID nao definido.")

    limits = Limits(
        max_emails_per_provider=int(os.environ.get("MAX_EMAILS_PER_PROVIDER", "25")),
    )

    return Settings(
        project_id=project_id,
        region=os.environ.get("REGION", "southamerica-east1"),
        dry_run=_env_bool("DRY_RUN", True),
        max_emails_per_provider=limits.max_emails_per_provider,
        accounts_config_path=os.environ.get("ACCOUNTS_CONFIG_PATH", str(Path("config") / "accounts.yaml")),
        feature_flags=FeatureFlags(
            outlook_enabled=_env_bool("OUTLOOK_ENABLED"),
            calendar_enabled=_env_bool("CALENDAR_ENABLED"),
            whatsapp_enabled=_env_bool("WHATSAPP_ENABLED"),
            ai_enabled=_env_bool("AI_ENABLED"),
            auto_execution_enabled=_env_bool("AUTO_EXECUTION_ENABLED"),
        ),
        limits=limits,
        calendar=CalendarSettings(
            enabled=_env_bool("CALENDAR_ENABLED"),
            provider=os.environ.get("CALENDAR_PROVIDER", "google"),
            lookahead_days=int(os.environ.get("CALENDAR_LOOKAHEAD_DAYS", "7")),
            lookback_days=int(os.environ.get("CALENDAR_LOOKBACK_DAYS", "1")),
            max_events=int(os.environ.get("CALENDAR_MAX_EVENTS", "100")),
            calendar_ids=tuple(item.strip() for item in os.environ.get("CALENDAR_IDS", "primary").split(",") if item.strip()),
            include_declined=_env_bool("CALENDAR_INCLUDE_DECLINED"),
            include_cancelled=_env_bool("CALENDAR_INCLUDE_CANCELLED"),
            workday_start=os.environ.get("CALENDAR_WORKDAY_START", "08:00"),
            workday_end=os.environ.get("CALENDAR_WORKDAY_END", "18:00"),
            min_free_window_minutes=int(os.environ.get("CALENDAR_MIN_FREE_WINDOW_MINUTES", "30")),
            timezone=os.environ.get("CALENDAR_TIMEZONE", "America/Sao_Paulo"),
        ),
    )
