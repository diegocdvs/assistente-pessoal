from __future__ import annotations

import ipaddress
import unicodedata

from app.security.models import DomainAssessment

COMMON_TLDS = {"com", "org", "net", "edu", "gov", "br", "dev", "io", "co", "ai"}
PROTECTED_DOMAINS = ("google.com", "microsoft.com", "paypal.com", "apple.com", "github.com", "openai.com")
HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "@": "a", "$": "s"})


class DomainAnalyzer:
    def analyze(self, value: str | None) -> DomainAssessment:
        domain = (value or "").strip().lower().strip(".")
        reasons: list[str] = []
        if not domain:
            return DomainAssessment(value="", normalized="", is_empty=True, risk_reasons=["empty_domain"])

        is_ip_literal = _is_ip_literal(domain)
        if is_ip_literal:
            reasons.append("ip_literal_domain")

        has_unicode = any(ord(char) > 127 for char in domain)
        if has_unicode:
            reasons.append("unicode_domain")

        has_punycode = "xn--" in domain
        if has_punycode:
            reasons.append("punycode_domain")

        tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
        uncommon_tld = bool(tld and tld not in COMMON_TLDS and not is_ip_literal)
        if uncommon_tld:
            reasons.append(f"uncommon_tld:{tld}")

        normalized = _normalize(domain)
        looks_like = _lookalike(normalized)
        if looks_like and looks_like != domain:
            reasons.append(f"lookalike_domain:{looks_like}")

        return DomainAssessment(
            value=domain,
            normalized=normalized,
            is_ip_literal=is_ip_literal,
            has_unicode=has_unicode,
            has_punycode=has_punycode,
            uncommon_tld=uncommon_tld,
            looks_like=looks_like,
            risk_reasons=reasons,
        )


def _is_ip_literal(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip("[]"))
        return True
    except ValueError:
        return False


def _normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return ascii_value.translate(HOMOGLYPHS)


def _lookalike(normalized: str) -> str | None:
    compact = normalized.replace("-", "").replace(".", "")
    for protected in PROTECTED_DOMAINS:
        protected_compact = protected.replace(".", "")
        if compact == protected_compact or _one_edit_apart(compact, protected_compact):
            return protected
    return None


def _one_edit_apart(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1:
        return False
    if left == right:
        return True
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    if len(left) > len(right):
        left, right = right, left
    index = edits = 0
    for char in right:
        if index < len(left) and left[index] == char:
            index += 1
        else:
            edits += 1
            if edits > 1:
                return False
    return True
