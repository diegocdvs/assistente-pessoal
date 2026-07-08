from __future__ import annotations

from app.core.models import ActionPlan, Category, Classification, EmailEntity, Priority


class AutomationPlanner:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def plan(self, email: EmailEntity, classification: Classification) -> list[ActionPlan]:
        plans: list[ActionPlan] = []

        if classification.priority == Priority.CRITICA:
            plans.append(self._plan("highlight_critical", "Prioridade critica exige destaque no relatorio."))

        if classification.priority == Priority.ALTA:
            plans.append(self._plan("review_high_priority", "Prioridade alta deve ser revisada."))

        if classification.category == Category.EVENTO:
            plans.append(self._plan("review_event_candidate", "Possivel evento detectado para revisao futura."))

        if classification.category == Category.FINANCEIRO:
            plans.append(self._plan("review_financial", "Mensagem financeira deve entrar no acompanhamento."))

        return plans

    def _plan(self, action_type: str, reason: str) -> ActionPlan:
        return ActionPlan(
            type=action_type,
            reason=reason,
            dry_run=self.dry_run,
            status="planned",
        )
