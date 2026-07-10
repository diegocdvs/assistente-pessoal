from __future__ import annotations

from typing import Protocol

from google.cloud import firestore

from app.daily_brief.models import DailyBrief


class DailyBriefRepository(Protocol):
    def save(self, brief: DailyBrief) -> str:
        pass

    def latest(self) -> DailyBrief | None:
        pass


class InMemoryDailyBriefRepository:
    def __init__(self) -> None:
        self.briefs: dict[str, DailyBrief] = {}

    def save(self, brief: DailyBrief) -> str:
        self.briefs[_key(brief)] = brief
        return _key(brief)

    def latest(self) -> DailyBrief | None:
        if not self.briefs:
            return None
        return sorted(self.briefs.values(), key=lambda brief: brief.generated_at)[-1]


class FirestoreDailyBriefRepository:
    def __init__(self, project_id: str) -> None:
        self.client = firestore.Client(project=project_id)

    def save(self, brief: DailyBrief) -> str:
        doc_id = _key(brief)
        self.client.collection("daily_briefs").document(doc_id).set(brief.to_dict(), merge=True)
        return doc_id

    def latest(self) -> DailyBrief | None:
        docs = list(self.client.collection("daily_briefs").order_by("generated_at", direction=firestore.Query.DESCENDING).limit(1).stream())
        if not docs:
            return None
        payload = docs[0].to_dict() or {}
        from app.daily_brief.models import DailyBriefSection

        payload["sections"] = [DailyBriefSection(**section) for section in payload.get("sections", [])]
        return DailyBrief(**payload)


def _key(brief: DailyBrief) -> str:
    scope = ",".join(brief.account_ids) if brief.account_ids else "all"
    return f"{brief.date}:{scope}".replace("/", "_")
