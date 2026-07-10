from __future__ import annotations

from app.security.models import AttachmentAssessment, HeaderAssessment, LinkAssessment, RiskLevel


class RiskEngine:
    def score(
        self,
        *,
        links: list[LinkAssessment],
        attachments: list[AttachmentAssessment],
        headers: HeaderAssessment,
        external_images: int = 0,
    ) -> tuple[int, RiskLevel, list[str]]:
        score = 0
        reasons: list[str] = []

        for link in links:
            if link.suspicious:
                score += 10 + len(link.risk_reasons) * 5
                reasons.extend([f"link:{reason}" for reason in link.risk_reasons])

        for attachment in attachments:
            if attachment.is_executable:
                score += 45
            if attachment.has_double_extension:
                score += 25
            if attachment.suspicious:
                reasons.extend([f"attachment:{reason}" for reason in attachment.risk_reasons])

        if headers.spoofing_signals:
            score += 20 + len(headers.spoofing_signals) * 10
            reasons.extend([f"spoofing:{reason}" for reason in headers.spoofing_signals])

        if headers.suspicious_headers:
            score += len(headers.suspicious_headers) * 8
            reasons.extend([f"header:{reason}" for reason in headers.suspicious_headers])

        if external_images:
            score += min(external_images * 4, 20)
            reasons.append("external_images")

        if headers.list_unsubscribe or headers.list_id:
            reasons.append("subscription_headers")

        score = min(score, 100)
        return score, _risk_level(score), sorted(set(reasons))


def _risk_level(score: int) -> RiskLevel:
    if score >= 85:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
