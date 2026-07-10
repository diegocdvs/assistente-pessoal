from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from app.security.domains import DomainAnalyzer
from app.security.models import LinkAssessment

URL_RE = re.compile(r"\b(?:https?://|mailto:)[^\s<>\"]+", re.IGNORECASE)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly"}
COMMON_PORTS = {80, 443, 25, 465, 587}


class LinkAnalyzer:
    def __init__(self, domain_analyzer: DomainAnalyzer | None = None) -> None:
        self.domain_analyzer = domain_analyzer or DomainAnalyzer()

    def extract(self, text: str) -> list[str]:
        return [match.group(0).rstrip(").,;]") for match in URL_RE.finditer(text or "")]

    def analyze_many(self, text: str) -> list[LinkAssessment]:
        return [self.analyze(url) for url in self.extract(text)]

    def analyze(self, url: str) -> LinkAssessment:
        parsed = urlparse(url)
        protocol = parsed.scheme.lower() or None
        domain = parsed.hostname.lower() if parsed.hostname else None
        reasons: list[str] = []

        if protocol not in {"http", "https", "mailto"}:
            reasons.append(f"unexpected_protocol:{protocol}")

        domain_assessment = self.domain_analyzer.analyze(domain)
        reasons.extend(domain_assessment.risk_reasons)

        is_shortener = bool(domain and domain in SHORTENERS)
        if is_shortener:
            reasons.append("url_shortener")

        if parsed.port and parsed.port not in COMMON_PORTS:
            reasons.append(f"uncommon_port:{parsed.port}")

        if _has_redirect_hint(parsed.query):
            reasons.append("redirect_parameter")

        return LinkAssessment(
            url=url,
            protocol=protocol,
            domain=domain,
            suspicious=bool(reasons),
            risk_reasons=reasons,
            is_ip_literal=domain_assessment.is_ip_literal,
            is_shortener=is_shortener,
            has_unicode=domain_assessment.has_unicode,
            has_punycode=domain_assessment.has_punycode,
            uncommon_port=parsed.port if parsed.port and parsed.port not in COMMON_PORTS else None,
        )


def _has_redirect_hint(query: str) -> bool:
    params = parse_qs(query)
    return any(key.lower() in {"url", "u", "redirect", "redirect_url", "target", "next"} for key in params)
