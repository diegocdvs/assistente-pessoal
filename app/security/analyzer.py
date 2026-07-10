from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.core.models import EmailEntity
from app.security.attachments import AttachmentAnalyzer
from app.security.events import SecurityEventFactory
from app.security.headers import HeaderAnalyzer
from app.security.links import LinkAnalyzer
from app.security.models import SecurityAssessment
from app.security.policy import SecurityPolicy
from app.security.risk import RiskEngine

IMG_RE = re.compile(r"<img[^>]+src=[\"']https?://", re.IGNORECASE)


class ThreatAnalyzer:
    def __init__(
        self,
        *,
        header_analyzer: HeaderAnalyzer | None = None,
        link_analyzer: LinkAnalyzer | None = None,
        attachment_analyzer: AttachmentAnalyzer | None = None,
        risk_engine: RiskEngine | None = None,
        policy: SecurityPolicy | None = None,
        event_factory: SecurityEventFactory | None = None,
    ) -> None:
        self.header_analyzer = header_analyzer or HeaderAnalyzer()
        self.link_analyzer = link_analyzer or LinkAnalyzer()
        self.attachment_analyzer = attachment_analyzer or AttachmentAnalyzer()
        self.risk_engine = risk_engine or RiskEngine()
        self.policy = policy or SecurityPolicy()
        self.event_factory = event_factory or SecurityEventFactory()

    def analyze(self, source: EmailEntity | dict[str, Any]) -> SecurityAssessment:
        payload = source.to_dict() if isinstance(source, EmailEntity) else dict(source)
        provider = str(payload.get("provider") or "unknown")
        source_id = str(payload.get("id") or payload.get("source_id") or "unknown")
        headers = self.header_analyzer.analyze(payload.get("raw_headers"))
        text = _analysis_text(payload)
        links = self.link_analyzer.analyze_many(text)
        attachments = self.attachment_analyzer.analyze_many(_attachments(payload))
        external_images = len(IMG_RE.findall(text))
        risk_score, risk_level, risk_reasons = self.risk_engine.score(
            links=links,
            attachments=attachments,
            headers=headers,
            external_images=external_images,
        )
        decision = self.policy.decide(risk_score=risk_score, risk_level=risk_level)
        events = self.event_factory.build(
            provider=provider,
            source_id=source_id,
            risk_level=risk_level,
            links=links,
            attachments=attachments,
            headers=headers,
        )
        return SecurityAssessment(
            assessment_id=f"security:{provider}:{source_id}:{uuid4().hex}",
            provider=provider,
            source_id=source_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            link_count=len(links),
            attachment_count=len(attachments),
            external_images=external_images,
            suspicious_headers=headers.suspicious_headers,
            spoofing_signals=headers.spoofing_signals,
            authentication_signals=headers.authentication_signals,
            policy_decision=decision,
            links=links,
            attachments=attachments,
            events=events,
        )


def _analysis_text(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return " ".join(
        str(value or "")
        for value in [
            payload.get("subject"),
            payload.get("snippet"),
            metadata.get("body"),
            metadata.get("html"),
            metadata.get("text"),
        ]
    )


def _attachments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    attachments = payload.get("attachments") or metadata.get("attachments") or []
    return attachments if isinstance(attachments, list) else []
