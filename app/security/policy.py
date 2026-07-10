from __future__ import annotations

from app.security.models import RiskLevel, SecurityDecision


class SecurityPolicy:
    def decide(self, *, risk_score: int, risk_level: RiskLevel) -> SecurityDecision:
        if risk_level == RiskLevel.CRITICAL or risk_score >= 85:
            return SecurityDecision.QUARANTINE
        if risk_score >= 75:
            return SecurityDecision.BLOCK
        if risk_level == RiskLevel.HIGH or risk_score >= 60:
            return SecurityDecision.REVIEW
        if risk_level == RiskLevel.MEDIUM or risk_score >= 30:
            return SecurityDecision.WARN
        return SecurityDecision.ALLOW
