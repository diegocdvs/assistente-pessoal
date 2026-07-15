from __future__ import annotations

from dataclasses import dataclass


RETRYABLE_CODES = {
    "timeout",
    "temporary_unavailable",
    "rate_limit",
    "http_5xx",
    "firestore_before_confirmed_delivery",
}
NON_RETRYABLE_CODES = {
    "missing_credentials",
    "insufficient_oauth_scope",
    "recipient_outside_allowlist",
    "invalid_configuration",
    "blocked_by_policy",
    "security_error",
    "invalid_content",
    "delivery_already_confirmed",
    "delivery_uncertain",
}


@dataclass(frozen=True)
class RetryDecision:
    retryable: bool
    reason: str


class ScheduledDailyBriefRetryPolicy:
    def __init__(self, *, max_attempts: int = 3) -> None:
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("DAILY_BRIEF_SCHEDULE_MAX_ATTEMPTS deve estar entre 1 e 5.")
        self.max_attempts = max_attempts

    def classify(self, *, error_code: str | None, attempt: int, possible_delivery: bool = False) -> RetryDecision:
        if possible_delivery:
            return RetryDecision(False, "possible delivery requires manual review")
        if attempt >= self.max_attempts:
            return RetryDecision(False, "max attempts reached")
        if error_code in RETRYABLE_CODES:
            return RetryDecision(True, f"retryable:{error_code}")
        if error_code in NON_RETRYABLE_CODES:
            return RetryDecision(False, f"non_retryable:{error_code}")
        return RetryDecision(False, f"unknown_non_retryable:{error_code or 'unknown'}")
