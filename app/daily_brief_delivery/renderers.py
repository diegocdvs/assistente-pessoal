from __future__ import annotations

import hashlib
import html
from datetime import datetime, timezone
from typing import Any

from app.daily_brief.models import DailyBrief
from app.daily_brief.renderers import DailyBriefTextRenderer
from app.daily_brief_delivery.models import DailyBriefEmailMessage


class DailyBriefSubjectBuilder:
    def build(self, brief: DailyBrief) -> str:
        suffix = {
            "OK": "Dia tranquilo",
            "WARNING": "Atencao necessaria",
            "ERROR": "Revisao necessaria",
        }.get(brief.status, "Resumo diario")
        return f"Daily Brief - {suffix} - {brief.date}"


class DailyBriefEmailRenderer:
    def __init__(
        self,
        *,
        text_renderer: DailyBriefTextRenderer | None = None,
        subject_builder: DailyBriefSubjectBuilder | None = None,
        max_items_per_section: int = 5,
    ) -> None:
        self.text_renderer = text_renderer or DailyBriefTextRenderer(max_items_per_section=max_items_per_section)
        self.subject_builder = subject_builder or DailyBriefSubjectBuilder()

    def render(self, brief: DailyBrief, *, account_id: str, recipient: str, mode: str) -> DailyBriefEmailMessage:
        idempotency_key = build_idempotency_key(brief.brief_id, account_id, recipient, mode)
        return DailyBriefEmailMessage(
            message_id=f"daily-brief-email:{_short_hash(idempotency_key)}",
            brief_id=brief.brief_id,
            account_id=account_id,
            recipient=recipient,
            subject=self.subject_builder.build(brief),
            text_body=self.text_renderer.render(brief),
            html_body=self._html(brief),
            delivery_mode=mode,
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _html(self, brief: DailyBrief) -> str:
        lines = [
            "<!doctype html>",
            "<html>",
            "<body>",
            "<h1>Daily Brief</h1>",
            f"<p><strong>Data:</strong> {html.escape(brief.date)}</p>",
            f"<p><strong>Status:</strong> {html.escape(brief.status)}</p>",
            f"<p>{html.escape(brief.headline)}</p>",
            "<h2>Resumo</h2>",
            "<ul>",
        ]
        metrics = brief.summary_metrics
        for label, value in [
            ("compromissos hoje", metrics.get("meetings_today", 0)),
            ("emails criticos", metrics.get("critical_emails_count", 0)),
            ("conflitos", metrics.get("conflicts_count", 0)),
            ("follow-ups", metrics.get("followups_count", 0)),
            ("auditoria", brief.last_audit_status),
        ]:
            lines.append(f"<li>{html.escape(str(value))} {html.escape(label)}</li>")
        lines.extend(["</ul>"])
        for title, items in [
            ("Agenda", brief.agenda_today),
            ("Prioridades", brief.top_priorities),
            ("Follow-ups", brief.followups),
            ("Seguranca", brief.security_warnings + brief.high_risk_items),
        ]:
            lines.extend(_section(title, items))
        lines.extend(["</body>", "</html>"])
        return "\n".join(lines)


def build_idempotency_key(brief_id: str, account_id: str, recipient: str, mode: str) -> str:
    material = "|".join([brief_id, account_id, recipient.strip().lower(), mode])
    return f"daily-brief:{_short_hash(material, length=32)}"


def _section(title: str, items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    lines = [f"<h2>{html.escape(title)}</h2>", "<ul>"]
    if not items:
        lines.append("<li>nenhum item</li>")
    for item in items[:limit]:
        label = item.get("title") or item.get("summary") or item.get("reason") or item.get("type") or item.get("id") or "item"
        lines.append(f"<li>{html.escape(str(label)[:120])}</li>")
    if len(items) > limit:
        lines.append(f"<li>mais {len(items) - limit} itens</li>")
    lines.append("</ul>")
    return lines


def _short_hash(value: str, *, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
