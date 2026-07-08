from __future__ import annotations

import pytest

from app.config import load_settings


def test_load_settings_defaults_feature_flags_to_disabled(monkeypatch):
    monkeypatch.setenv("PROJECT_ID", "project")
    monkeypatch.delenv("OUTLOOK_ENABLED", raising=False)
    monkeypatch.delenv("CALENDAR_ENABLED", raising=False)
    monkeypatch.delenv("WHATSAPP_ENABLED", raising=False)
    monkeypatch.delenv("AI_ENABLED", raising=False)
    monkeypatch.delenv("AUTO_EXECUTION_ENABLED", raising=False)

    settings = load_settings()

    assert settings.project_id == "project"
    assert settings.region == "southamerica-east1"
    assert settings.dry_run is True
    assert settings.feature_flags.outlook_enabled is False
    assert settings.feature_flags.calendar_enabled is False
    assert settings.feature_flags.whatsapp_enabled is False
    assert settings.feature_flags.ai_enabled is False
    assert settings.feature_flags.auto_execution_enabled is False
    assert settings.limits.max_emails_per_provider == 25


def test_load_settings_reads_env_flags_and_limits(monkeypatch):
    monkeypatch.setenv("PROJECT_ID", "project")
    monkeypatch.setenv("REGION", "us-central1")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("ACCOUNTS_CONFIG_PATH", "config/custom.yaml")
    monkeypatch.setenv("MAX_EMAILS_PER_PROVIDER", "7")
    monkeypatch.setenv("OUTLOOK_ENABLED", "true")
    monkeypatch.setenv("CALENDAR_ENABLED", "1")
    monkeypatch.setenv("WHATSAPP_ENABLED", "yes")
    monkeypatch.setenv("AI_ENABLED", "y")
    monkeypatch.setenv("AUTO_EXECUTION_ENABLED", "on")

    settings = load_settings()

    assert settings.region == "us-central1"
    assert settings.dry_run is False
    assert settings.accounts_config_path == "config/custom.yaml"
    assert settings.max_emails_per_provider == 7
    assert settings.limits.max_emails_per_provider == 7
    assert settings.feature_flags.outlook_enabled is True
    assert settings.feature_flags.calendar_enabled is True
    assert settings.feature_flags.whatsapp_enabled is True
    assert settings.feature_flags.ai_enabled is True
    assert settings.feature_flags.auto_execution_enabled is True


def test_load_settings_requires_project_id(monkeypatch):
    monkeypatch.delenv("PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    with pytest.raises(RuntimeError, match="PROJECT_ID"):
        load_settings()
