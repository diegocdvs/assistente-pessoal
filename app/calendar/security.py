from __future__ import annotations

from urllib.parse import urlparse

from app.calendar.models import CalendarEvent
from app.security import SecurityDecision
from app.security.domains import DomainAnalyzer
from app.security.links import LinkAnalyzer
from app.security.models import RiskLevel, SecurityAssessment


class CalendarSecurityAnalyzer:
    def __init__(self, link_analyzer: LinkAnalyzer | None = None, domain_analyzer: DomainAnalyzer | None = None) -> None:
        self.link_analyzer = link_analyzer or LinkAnalyzer()
        self.domain_analyzer = domain_analyzer or DomainAnalyzer()

    def analyze(self, event: CalendarEvent, *, user_domain: str | None = None) -> SecurityAssessment:
        text = " ".join(value for value in [event.title, event.description_summary, event.location] if value)
        links = self.link_analyzer.analyze_many(text)
        reasons: list[str] = []
        if event.meeting_url_present:
            reasons.append("meeting_url_present")
        if event.organizer and user_domain and event.organizer.split("@")[-1].lower() != user_domain.lower():
            reasons.append("external_organizer")
        organizer_domain = event.organizer.split("@")[-1] if event.organizer and "@" in event.organizer else None
        domain_assessment = self.domain_analyzer.analyze(organizer_domain)
        reasons.extend(domain_assessment.risk_reasons)
        for link in links:
            if link.suspicious:
                reasons.extend(link.risk_reasons)
        score = min(100, len(set(reasons)) * 15 + len([link for link in links if link.suspicious]) * 20)
        level = RiskLevel.CRITICAL if score >= 85 else RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW
        decision = SecurityDecision.REVIEW if level in {RiskLevel.HIGH, RiskLevel.CRITICAL} else SecurityDecision.WARN if level == RiskLevel.MEDIUM else SecurityDecision.ALLOW
        return SecurityAssessment(
            assessment_id=f"calendar-security:{event.provider}:{event.id}",
            provider=event.provider,
            source_id=event.id,
            risk_score=score,
            risk_level=level,
            risk_reasons=sorted(set(reasons)),
            link_count=len(links),
            attachment_count=0,
            external_images=0,
            suspicious_headers=[],
            spoofing_signals=[],
            authentication_signals=[],
            policy_decision=decision,
            links=links,
        )
