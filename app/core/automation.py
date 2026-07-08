from __future__ import annotations

from app.core.models import ActionPlan, Category, Classification, EmailEntity, Priority


class AutomationPlanner:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def plan(self, email: EmailEntity, classification: Classification) -> list[ActionPlan]:
        plans: list[ActionPlan] = []

        if classification.priority == Priority.CRITICA:
            plans.append(
                self._plan(
                    "highlight_critical",
                    "Prioridade critica exige destaque no relatorio.",
                    email,
                    classification,
                )
            )

        if classification.priority == Priority.ALTA:
            plans.append(
                self._plan(
                    "review_high_priority",
                    "Prioridade alta deve ser revisada.",
                    email,
                    classification,
                )
            )

        if classification.possible_event:
            plans.append(
                self._plan(
                    "review_event_candidate",
                    "Possivel evento detectado para revisao futura.",
                    email,
                    classification,
                )
            )

        if classification.category == Category.FINANCEIRO:
            plans.append(
                self._plan(
                    "review_financial",
                    "Mensagem financeira deve entrar no acompanhamento.",
                    email,
                    classification,
                )
            )

        return plans

    def _plan(
        self,
        action_type: str,
        reason: str,
        email: EmailEntity,
        classification: Classification,
    ) -> ActionPlan:
        return ActionPlan(
            type=action_type,
            reason=reason,
            dry_run=self.dry_run,
            status="planned",
            payload={
                "email_id": email.id,
                "account_id": email.account_id,
                "provider": email.provider,
                "category": classification.category.value,
                "priority": classification.priority.value,
            },
            id=f"{email.account_id}:{email.id}:{action_type}".replace("/", "_"),
            source="rule_based_classifier",
            audit_metadata={
                "email_id": email.id,
                "thread_id": email.thread_id,
                "account_id": email.account_id,
                "provider": email.provider,
                "classification_reason": classification.reason,
                "classification_confidence": classification.confidence,
            },
        )
