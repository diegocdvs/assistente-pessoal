from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.daily_brief.models import DailyBrief


class DailyBriefJsonRenderer:
    def render(self, brief: DailyBrief) -> str:
        return json.dumps(brief.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


class DailyBriefTextRenderer:
    def __init__(self, *, max_items_per_section: int = 5) -> None:
        self.max_items = max_items_per_section

    def render(self, brief: DailyBrief) -> str:
        lines = [
            "DAILY BRIEF",
            f"Data: {brief.date}",
            f"Status: {brief.status}",
            "",
            "Resumo",
            f"- {brief.summary_metrics.get('meetings_today', 0)} compromissos hoje",
            f"- {brief.summary_metrics.get('critical_emails_count', 0)} emails criticos",
            f"- {brief.summary_metrics.get('conflicts_count', 0)} conflitos",
            f"- {brief.summary_metrics.get('followups_count', 0)} follow-ups",
            f"- auditoria: {brief.last_audit_status}",
            "",
            "Headline",
            f"- {brief.headline}",
        ]
        if brief.next_event:
            lines.extend(["", "Proximo compromisso", f"- {_time(brief.next_event.get('start_at'), brief.timezone)} - {_title(brief.next_event)}"])
        lines.extend(_items("Agenda", brief.agenda_today, brief.timezone, self.max_items))
        lines.extend(_items("Janelas livres", brief.free_windows_today, brief.timezone, self.max_items, free_window=True))
        lines.extend(_items("Prioridades", brief.top_priorities, brief.timezone, self.max_items))
        lines.extend(_items("Follow-ups", brief.followups, brief.timezone, self.max_items))
        lines.extend(_items("Seguranca", brief.security_warnings + brief.high_risk_items, brief.timezone, self.max_items))
        return "\n".join(lines)


def _items(title: str, items: list[dict[str, Any]], timezone_name: str, limit: int, *, free_window: bool = False) -> list[str]:
    lines = ["", title]
    shown = items[:limit]
    if not shown:
        lines.append("- nenhum item")
        return lines
    for item in shown:
        if free_window:
            lines.append(f"- {_time(item.get('start_at'), timezone_name)}-{_time(item.get('end_at'), timezone_name)}")
        else:
            label = item.get("title") or item.get("summary") or item.get("reason") or item.get("type") or item.get("id") or "item"
            when = _time(item.get("start_at") or item.get("created_at"), timezone_name)
            lines.append(f"- {when + ' - ' if when else ''}{str(label)[:80]}")
    if len(items) > limit:
        lines.append(f"- ... mais {len(items) - limit} itens")
    return lines


def _time(value: Any, timezone_name: str) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) == 10:
        return "dia inteiro"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(ZoneInfo(timezone_name)).strftime("%H:%M")
    except ValueError:
        return ""


def _title(item: dict[str, Any]) -> str:
    return str(item.get("title") or "(sem titulo)")[:80]
