from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.context.models import ContextSnapshot
from app.daily_brief.models import DailyBrief, DailyBriefSection


SECTION_ORDER = ("agenda", "priorities", "email", "followups", "subscriptions", "security", "audit")


class DailyBriefBuilder:
    def __init__(self, *, max_items_per_section: int = 5, include_tomorrow: bool = True) -> None:
        if max_items_per_section < 1 or max_items_per_section > 50:
            raise ValueError("DAILY_BRIEF_MAX_ITEMS_PER_SECTION deve estar entre 1 e 50.")
        self.max_items = max_items_per_section
        self.include_tomorrow = include_tomorrow

    def build(
        self,
        snapshot: ContextSnapshot,
        *,
        account_ids: list[str] | None = None,
        timezone_name: str = "America/Sao_Paulo",
        audit_status: str = "unknown",
        audit_at: str | None = None,
        open_discrepancies: list[dict[str, Any]] | None = None,
    ) -> DailyBrief:
        ZoneInfo(timezone_name)
        open_discrepancies = open_discrepancies or []
        agenda_today = _limit(snapshot.calendar_events_today, self.max_items)
        agenda_tomorrow = _limit(snapshot.calendar_events_tomorrow, self.max_items) if self.include_tomorrow else []
        critical_emails = _limit(snapshot.emails_critical, self.max_items)
        top_priorities = _limit([item.to_dict() for item in snapshot.top_priorities], self.max_items)
        followups = _limit([item.to_dict() for item in snapshot.followups], self.max_items)
        pending_actions = _limit(_pending_actions(snapshot.action_plans), self.max_items)
        subscriptions = _limit(snapshot.top_subscription_candidates, self.max_items)
        security_warnings = _limit(snapshot.calendar_security_warnings + snapshot.warning_items, self.max_items)
        high_risk_items = _limit(snapshot.high_risk_items, self.max_items)
        metrics = _metrics(
            meetings_today=len(snapshot.calendar_events_today),
            meetings_tomorrow=len(snapshot.calendar_events_tomorrow),
            free_windows_count=len(snapshot.free_windows_today),
            conflicts_count=len(snapshot.calendar_conflicts),
            critical_emails_count=len(snapshot.emails_critical),
            top_priorities_count=len(snapshot.top_priorities),
            followups_count=len(snapshot.followups),
            pending_action_plans_count=len(_pending_actions(snapshot.action_plans)),
            subscriptions_recommended_count=snapshot.subscriptions_recommended_for_unsubscribe,
            subscriptions_waiting_approval_count=snapshot.subscriptions_waiting_approval,
            security_warnings_count=len(snapshot.calendar_security_warnings + snapshot.warning_items),
            high_risk_items_count=len(snapshot.high_risk_items),
            open_discrepancies_count=len(open_discrepancies),
        )
        status = _status(metrics, audit_status, open_discrepancies)
        headline = _headline(status, metrics)
        sections = [
            _section("agenda", "Agenda", 10, "WARNING" if snapshot.calendar_conflicts else "OK", agenda_today, f"{metrics['meetings_today']} compromissos hoje."),
            _section("priorities", "Prioridades", 20, "WARNING" if top_priorities else "OK", top_priorities, f"{metrics['top_priorities_count']} prioridades."),
            _section("email", "Email", 30, "WARNING" if critical_emails else "OK", critical_emails, f"{metrics['critical_emails_count']} emails criticos."),
            _section("followups", "Follow-ups", 40, "WARNING" if followups else "OK", followups, f"{metrics['followups_count']} follow-ups."),
            _section("subscriptions", "Subscriptions", 50, "WARNING" if subscriptions else "OK", subscriptions, f"{metrics['subscriptions_recommended_count']} recomendadas."),
            _section("security", "Seguranca", 60, "WARNING" if security_warnings or high_risk_items else "OK", security_warnings + high_risk_items, f"{metrics['security_warnings_count']} alertas."),
            _section("audit", "Auditoria", 70, "ERROR" if audit_status == "ERROR" else "WARNING" if audit_status == "WARNING" else "OK", open_discrepancies, f"auditoria: {audit_status}."),
        ]
        return DailyBrief(
            brief_id=f"daily-brief:{snapshot.date}:{','.join(account_ids or ['all'])}",
            date=snapshot.date,
            timezone=timezone_name,
            generated_at=datetime.now(timezone.utc).isoformat(),
            account_ids=account_ids or [],
            status=status,
            headline=headline,
            agenda_today=agenda_today,
            agenda_tomorrow=agenda_tomorrow,
            next_event=snapshot.next_event,
            free_windows_today=_limit(snapshot.free_windows_today, self.max_items),
            calendar_conflicts=_limit(snapshot.calendar_conflicts, self.max_items),
            critical_emails=critical_emails,
            top_priorities=top_priorities,
            followups=followups,
            pending_action_plans=pending_actions,
            subscriptions_recommended=subscriptions,
            subscriptions_waiting_approval=snapshot.subscriptions_waiting_approval,
            security_warnings=security_warnings,
            high_risk_items=high_risk_items,
            last_audit_status=audit_status,
            last_audit_at=audit_at,
            open_discrepancies=open_discrepancies,
            summary_metrics=metrics,
            sections=sections,
        )


def _limit(items: list[Any], limit: int) -> list[Any]:
    return list(items or [])[:limit]


def _pending_actions(action_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [plan for plan in action_plans if plan.get("status", "planned") in {"planned", "waiting_approval", "failed"}]


def _metrics(**values: int) -> dict[str, int]:
    return dict(values)


def _status(metrics: dict[str, int], audit_status: str, discrepancies: list[dict[str, Any]]) -> str:
    if audit_status == "ERROR" and any(item.get("severity") == "critical" for item in discrepancies):
        return "ERROR"
    if any(metrics[key] > 0 for key in ("critical_emails_count", "conflicts_count", "security_warnings_count", "high_risk_items_count", "followups_count")):
        return "WARNING"
    if audit_status == "WARNING":
        return "WARNING"
    return "OK"


def _headline(status: str, metrics: dict[str, int]) -> str:
    critical = metrics["critical_emails_count"] + metrics["high_risk_items_count"]
    if status == "ERROR":
        return "Erro: auditoria critica aberta requer revisao."
    if critical or metrics["conflicts_count"]:
        return f"Atencao: {critical} itens criticos e {metrics['conflicts_count']} conflitos de agenda."
    if metrics["meetings_today"] or metrics["followups_count"] or metrics["security_warnings_count"]:
        return (
            f"Hoje ha {metrics['meetings_today']} compromissos, "
            f"{metrics['followups_count']} follow-ups e {metrics['security_warnings_count']} alertas de seguranca."
        )
    return "Dia tranquilo: nenhuma pendencia critica."


def _section(key: str, title: str, priority: int, status: str, items: list[dict[str, Any]], summary: str) -> DailyBriefSection:
    return DailyBriefSection(key=key, title=title, priority=priority, status=status, items=items, summary=summary, count=len(items))
