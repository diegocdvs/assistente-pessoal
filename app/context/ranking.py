from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.context.models import RankedWorkItem

PRIORITY_SCORE = {
    "critica": 100,
    "alta": 70,
    "normal": 35,
    "baixa": 10,
    "ruido": -20,
}

CATEGORY_SCORE = {
    "seguranca": 35,
    "financeiro": 30,
    "saude": 28,
    "trabalho": 24,
    "evento": 22,
    "viagem": 18,
    "entrega": 14,
    "compra": 10,
    "educacao": 8,
    "sistema": 8,
    "social": 2,
    "newsletter": -10,
    "promocao": -15,
    "outros": 0,
}

ACTION_SCORE = {
    "planned": 20,
    "waiting_approval": 25,
    "skipped": -10,
    "executed": -20,
    "failed": 18,
}


class PriorityRanker:
    def rank(
        self,
        work_items: list[dict[str, Any]],
        classifications: dict[str, dict[str, Any]],
        action_plans: dict[str, list[dict[str, Any]]],
        followup_ids: set[str] | None = None,
        *,
        limit: int = 10,
        now: datetime | None = None,
    ) -> list[RankedWorkItem]:
        now = now or datetime.now(timezone.utc)
        followup_ids = followup_ids or set()
        ranked = [
            self.score_item(
                work_item,
                classifications.get(_item_message_id(work_item), {}),
                action_plans.get(_item_message_id(work_item), []),
                is_followup=_item_message_id(work_item) in followup_ids or work_item.get("id") in followup_ids,
                now=now,
            )
            for work_item in work_items
        ]
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:limit]

    def score_item(
        self,
        work_item: dict[str, Any],
        classification: dict[str, Any],
        action_plans: list[dict[str, Any]],
        *,
        is_followup: bool = False,
        now: datetime | None = None,
    ) -> RankedWorkItem:
        now = now or datetime.now(timezone.utc)
        score = 0
        reasons: list[str] = []

        priority = classification.get("priority")
        if priority in PRIORITY_SCORE:
            score += PRIORITY_SCORE[priority]
            reasons.append(f"priority:{priority}")

        category = classification.get("category")
        if category in CATEGORY_SCORE:
            score += CATEGORY_SCORE[category]
            reasons.append(f"category:{category}")

        age_days = _age_days(_item_received_at(work_item), now)
        if age_days is not None:
            if age_days <= 1:
                score += 8
                reasons.append("recent")
            elif age_days >= 7:
                score += 12
                reasons.append("old_pending")
            elif age_days >= 3:
                score += 6
                reasons.append("aging")

        for action in action_plans:
            status = action.get("status", "planned")
            score += ACTION_SCORE.get(status, 8)
            reasons.append(f"action:{action.get('type', 'unknown')}:{status}")

        if is_followup:
            score += 35
            reasons.append("followup")

        return RankedWorkItem(work_item=work_item, score=score, reasons=reasons)


def _item_message_id(work_item: dict[str, Any]) -> str:
    payload = work_item.get("payload") or {}
    return str(payload.get("id") or payload.get("email_id") or work_item.get("id", ""))


def _item_received_at(work_item: dict[str, Any]) -> str | None:
    payload = work_item.get("payload") or {}
    value = payload.get("received_at") or work_item.get("created_at")
    return str(value) if value else None


def _age_days(value: str | None, now: datetime) -> int | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return max((now - parsed).days, 0)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
