"""Tests for the hybrid diagnoser (Gemini primary + rules fallback)."""
from __future__ import annotations

from datetime import datetime, timezone

from recoverops.models import AtRiskRecord, Diagnosis
from recoverops.reasoning.hybrid import HybridDiagnoser
from recoverops.reasoning.rules import RuleBasedDiagnoser
from recoverops.reasoning.signals import signals_from_record
from recoverops.taxonomy import RecordType, RootCause


def _record() -> AtRiskRecord:
    return AtRiskRecord(
        record_id="rec_hybrid_1",
        record_type=RecordType.FAILED_PAYMENT,
        merchant_id="m",
        customer_id="c",
        amount_paise=100,
        error_code="GATEWAY_ERROR:issuer_down",
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


class _StubPrimary:
    """A minimal stand-in for GeminiDiagnoser."""

    name = "stub"

    def __init__(self, *, diagnosis: Diagnosis | None = None, raises: Exception | None = None) -> None:
        self._d = diagnosis
        self._raises = raises

    def diagnose(self, signals):  # noqa: ANN001, D401
        if self._raises is not None:
            raise self._raises
        return self._d.model_copy(update={"record_id": signals.record_id})  # type: ignore[union-attr]


def test_primary_success_returns_primary_diagnosis() -> None:
    primary = _StubPrimary(
        diagnosis=Diagnosis(
            record_id="_",
            root_cause=RootCause.GATEWAY_DOWNTIME,
            confidence=0.9,
            reasoning="stub",
        )
    )
    hybrid = HybridDiagnoser(primary=primary, fallback=RuleBasedDiagnoser())
    d = hybrid.diagnose(signals_from_record(_record()))
    assert d.root_cause is RootCause.GATEWAY_DOWNTIME
    assert d.reasoning == "stub"
    assert hybrid.stats.primary_used == 1
    assert hybrid.stats.fallback_error == 0
    assert hybrid.stats.fallback_low_conf == 0


def test_primary_raises_triggers_fallback_and_tags() -> None:
    primary = _StubPrimary(raises=RuntimeError("429 quota exceeded"))
    hybrid = HybridDiagnoser(primary=primary, fallback=RuleBasedDiagnoser())
    d = hybrid.diagnose(signals_from_record(_record()))
    # rule engine hits GATEWAY_DOWNTIME from the error code
    assert d.root_cause is RootCause.GATEWAY_DOWNTIME
    assert d.reasoning.startswith("[fallback:error]")
    assert hybrid.stats.fallback_error == 1
    assert hybrid.stats.errors and "quota" in hybrid.stats.errors[0]


def test_low_confidence_primary_triggers_fallback() -> None:
    primary = _StubPrimary(
        diagnosis=Diagnosis(
            record_id="_",
            root_cause=RootCause.UNKNOWN,
            confidence=0.1,
            reasoning="unsure",
        )
    )
    hybrid = HybridDiagnoser(
        primary=primary, fallback=RuleBasedDiagnoser(), min_confidence=0.5
    )
    d = hybrid.diagnose(signals_from_record(_record()))
    # Fallback rules should recover the real cause from the error code.
    assert d.root_cause is RootCause.GATEWAY_DOWNTIME
    assert d.reasoning.startswith("[fallback:low_conf]")
    assert hybrid.stats.fallback_low_conf == 1


def test_stats_total_tracks_all_paths() -> None:
    good = _StubPrimary(
        diagnosis=Diagnosis(
            record_id="_",
            root_cause=RootCause.INSUFFICIENT_FUNDS,
            confidence=0.9,
            reasoning="",
        )
    )
    hybrid = HybridDiagnoser(primary=good, fallback=RuleBasedDiagnoser())
    for _ in range(3):
        hybrid.diagnose(signals_from_record(_record()))
    assert hybrid.stats.total == 3
    assert hybrid.stats.primary_used == 3
