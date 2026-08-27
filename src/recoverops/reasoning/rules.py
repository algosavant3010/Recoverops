"""Deterministic rule-based diagnoser.

Serves two purposes:
  1. Zero-cost fallback when the Gemini API is unavailable or rate-limited.
  2. A published baseline the evaluation harness compares Gemini against —
     if the LLM can't beat rules, it doesn't belong in the loop.
"""
from __future__ import annotations

from ..models import Diagnosis
from ..taxonomy import ERROR_CODES_BY_CAUSE, RecordType, RootCause
from .signals import RecordSignals

# Reverse index: error_code → cause. Built once at import time.
_CODE_TO_CAUSE: dict[str, RootCause] = {
    code: cause for cause, codes in ERROR_CODES_BY_CAUSE.items() for code in codes
}

_FRAUD_FLAGS = frozenset(
    {"velocity_spike", "bin_mismatch", "geo_anomaly", "device_reuse"}
)


class RuleBasedDiagnoser:
    """Priority-ordered rules. First match wins."""

    name = "rules_v1"

    def diagnose(self, signals: RecordSignals) -> Diagnosis:
        # 1. Explicit fraud risk flags win over any other signal.
        if any(f in _FRAUD_FLAGS for f in signals.risk_flags):
            return self._diag(
                signals,
                RootCause.FRAUD_SUSPECTED,
                confidence=0.9,
                reasoning=f"risk flags present: {sorted(set(signals.risk_flags))}",
                signals_used=["risk_flags"],
            )

        # 2. Error code → cause reverse index.
        if signals.error_code and signals.error_code in _CODE_TO_CAUSE:
            cause = _CODE_TO_CAUSE[signals.error_code]
            return self._diag(
                signals,
                cause,
                confidence=0.85,
                reasoning=f"error code '{signals.error_code}' maps to {cause.value}",
                signals_used=["error_code"],
            )

        # 3. Record-type fallbacks for causes with no error signal.
        if signals.record_type is RecordType.ABANDONED_CHECKOUT:
            return self._diag(
                signals,
                RootCause.CHECKOUT_ABANDONED,
                confidence=0.9,
                reasoning="abandoned checkout with no payment attempt",
                signals_used=["record_type", "has_prior_attempt"],
            )
        if signals.record_type is RecordType.OVERDUE_INVOICE:
            return self._diag(
                signals,
                RootCause.B2B_OVERDUE,
                confidence=0.9,
                reasoning="B2B invoice past due date",
                signals_used=["record_type"],
            )
        if signals.record_type is RecordType.FAILED_SUBSCRIPTION:
            return self._diag(
                signals,
                RootCause.MANDATE_LAPSED,
                confidence=0.55,
                reasoning="failed subscription without a specific error → likely mandate issue",
                signals_used=["record_type"],
            )

        # 4. No confident classification.
        return self._diag(
            signals,
            RootCause.UNKNOWN,
            confidence=0.3,
            reasoning="no strong signal available",
            signals_used=[],
        )

    def _diag(
        self,
        signals: RecordSignals,
        cause: RootCause,
        *,
        confidence: float,
        reasoning: str,
        signals_used: list[str],
    ) -> Diagnosis:
        return Diagnosis(
            record_id=signals.record_id,
            root_cause=cause,
            confidence=confidence,
            reasoning=reasoning,
            signals_used=signals_used,
        )
