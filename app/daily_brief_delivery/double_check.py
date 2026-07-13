from __future__ import annotations

from dataclasses import dataclass

from app.daily_brief_delivery.models import DailyBriefDeliveryRecord


@dataclass(frozen=True)
class DailyBriefDeliveryFinding:
    type: str
    severity: str
    message: str


class DailyBriefDeliveryDoubleCheck:
    def inspect(self, records: list[DailyBriefDeliveryRecord]) -> list[DailyBriefDeliveryFinding]:
        findings: list[DailyBriefDeliveryFinding] = []
        for record in records:
            if record.mode == "send" and record.status == "sent" and record.policy_decision != "ALLOW_SEND":
                findings.append(
                    DailyBriefDeliveryFinding(
                        "delivery_sent_without_allow_send_policy",
                        "critical",
                        f"Delivery {record.delivery_id} foi enviado sem policy ALLOW_SEND.",
                    )
                )
            if record.status in {"sent", "draft_created"} and record.error:
                findings.append(
                    DailyBriefDeliveryFinding(
                        "successful_delivery_with_error",
                        "high",
                        f"Delivery {record.delivery_id} marcou sucesso com erro.",
                    )
                )
        return findings
