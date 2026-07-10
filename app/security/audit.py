from __future__ import annotations

from app.security.models import SecurityAssessment, SecurityAuditRecord


class SecurityAuditor:
    def record(self, assessment: SecurityAssessment) -> SecurityAuditRecord:
        return SecurityAuditRecord(
            assessment_id=assessment.assessment_id,
            source_id=assessment.source_id,
            provider=assessment.provider,
            decision=assessment.policy_decision,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            reason_count=len(assessment.risk_reasons),
            metadata={
                "link_count": assessment.link_count,
                "attachment_count": assessment.attachment_count,
                "event_count": len(assessment.events),
            },
        )
