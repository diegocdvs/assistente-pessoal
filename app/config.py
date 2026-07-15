from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.calendar.config import CalendarSettings
from app.daily_brief_delivery.policy import DeliveryPolicySettings
from app.scheduled_daily_brief.service import ScheduledDailyBriefSettings


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
class DailyBriefSettings:
    enabled: bool = True
    timezone: str = "America/Sao_Paulo"
    max_items_per_section: int = 5
    persist: bool = True
    include_tomorrow: bool = True
    include_low_priority: bool = False

    def validate(self) -> None:
        from zoneinfo import ZoneInfo

        ZoneInfo(self.timezone)
        if self.max_items_per_section < 1 or self.max_items_per_section > 50:
            raise ValueError("DAILY_BRIEF_MAX_ITEMS_PER_SECTION deve estar entre 1 e 50.")


@dataclass(frozen=True)
class DailyBriefDeliverySettings(DeliveryPolicySettings):
    sender_account_id: str = "pessoal_google"
    secret_prefix: str = "google-pessoal"
    force: bool = False

    def validate(self) -> None:
        from zoneinfo import ZoneInfo

        if self.mode not in {"disabled", "draft", "send"}:
            raise ValueError("DAILY_BRIEF_DELIVERY_MODE deve ser disabled, draft ou send.")
        if "*" in self.recipients:
            raise ValueError("DAILY_BRIEF_DELIVERY_RECIPIENTS nao aceita wildcard.")
        if self.start_hour < 0 or self.start_hour > 23 or self.end_hour < 0 or self.end_hour > 24:
            raise ValueError("Janela de entrega do Daily Brief invalida.")
        ZoneInfo(self.timezone)


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
    daily_brief: DailyBriefSettings = field(default_factory=DailyBriefSettings)
    daily_brief_delivery: DailyBriefDeliverySettings = field(default_factory=DailyBriefDeliverySettings)
    scheduled_daily_brief: ScheduledDailyBriefSettings = field(default_factory=ScheduledDailyBriefSettings)


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
        daily_brief=DailyBriefSettings(
            enabled=_env_bool("DAILY_BRIEF_ENABLED", True),
            timezone=os.environ.get("DAILY_BRIEF_TIMEZONE", "America/Sao_Paulo"),
            max_items_per_section=int(os.environ.get("DAILY_BRIEF_MAX_ITEMS_PER_SECTION", "5")),
            persist=_env_bool("DAILY_BRIEF_PERSIST", True),
            include_tomorrow=_env_bool("DAILY_BRIEF_INCLUDE_TOMORROW", True),
            include_low_priority=_env_bool("DAILY_BRIEF_INCLUDE_LOW_PRIORITY", False),
        ),
        daily_brief_delivery=DailyBriefDeliverySettings(
            enabled=_env_bool("DAILY_BRIEF_DELIVERY_ENABLED", False),
            mode=os.environ.get("DAILY_BRIEF_DELIVERY_MODE", "disabled"),
            recipients=tuple(
                item.strip()
                for item in os.environ.get("DAILY_BRIEF_DELIVERY_RECIPIENTS", "").split(",")
                if item.strip()
            ),
            allow_send=_env_bool("DAILY_BRIEF_DELIVERY_ALLOW_SEND", False),
            start_hour=int(os.environ.get("DAILY_BRIEF_DELIVERY_START_HOUR", "5")),
            end_hour=int(os.environ.get("DAILY_BRIEF_DELIVERY_END_HOUR", "11")),
            timezone=os.environ.get("DAILY_BRIEF_DELIVERY_TIMEZONE", os.environ.get("DAILY_BRIEF_TIMEZONE", "America/Sao_Paulo")),
            sender_account_id=os.environ.get("DAILY_BRIEF_DELIVERY_SENDER_ACCOUNT_ID", "pessoal_google"),
            secret_prefix=os.environ.get("DAILY_BRIEF_DELIVERY_SECRET_PREFIX", "google-pessoal"),
            force=_env_bool("DAILY_BRIEF_DELIVERY_FORCE", False),
        ),
        scheduled_daily_brief=ScheduledDailyBriefSettings(
            enabled=_env_bool("DAILY_BRIEF_SCHEDULE_ENABLED", False),
            schedule_time=os.environ.get("DAILY_BRIEF_SCHEDULE_TIME", "07:30"),
            timezone=os.environ.get("DAILY_BRIEF_SCHEDULE_TIMEZONE", "America/Sao_Paulo"),
            mode=os.environ.get("DAILY_BRIEF_SCHEDULE_MODE", "draft"),
            account_scope=os.environ.get("DAILY_BRIEF_SCHEDULE_ACCOUNT_SCOPE", "all"),
            recipients=tuple(
                item.strip()
                for item in os.environ.get("DAILY_BRIEF_SCHEDULE_RECIPIENTS", "").split(",")
                if item.strip()
            ),
            max_attempts=int(os.environ.get("DAILY_BRIEF_SCHEDULE_MAX_ATTEMPTS", "3")),
            retry_delay_seconds=int(os.environ.get("DAILY_BRIEF_SCHEDULE_RETRY_DELAY_SECONDS", "60")),
            lookback_hours=int(os.environ.get("DAILY_BRIEF_SCHEDULE_LOOKBACK_HOURS", "24")),
        ),
    )
