from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DailyBriefDiscrepancy:
    type: str
    severity: str
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DailyBriefDoubleCheck:
    def inspect(self, brief: dict[str, Any], *, context_snapshot: dict[str, Any] | None = None, persistence_configured: bool = False) -> list[DailyBriefDiscrepancy]:
        discrepancies: list[DailyBriefDiscrepancy] = []
        if not brief.get("schema_version"):
            discrepancies.append(DailyBriefDiscrepancy("daily_brief_missing_schema_version", "error"))
        metrics = brief.get("summary_metrics") or {}
        if metrics.get("meetings_today") != len(brief.get("agenda_today") or []):
            discrepancies.append(DailyBriefDiscrepancy("daily_brief_metric_mismatch", "warning", {"metric": "meetings_today"}))
        if brief.get("status") == "OK" and (metrics.get("high_risk_items_count", 0) > 0 or metrics.get("security_warnings_count", 0) > 0):
            discrepancies.append(DailyBriefDiscrepancy("daily_brief_status_incompatible_with_risk", "error"))
        if persistence_configured and not brief.get("brief_id"):
            discrepancies.append(DailyBriefDiscrepancy("daily_brief_persistence_missing", "error"))
        if context_snapshot and brief.get("date") != context_snapshot.get("date"):
            discrepancies.append(DailyBriefDiscrepancy("daily_brief_wrong_date", "warning"))
        return discrepancies
