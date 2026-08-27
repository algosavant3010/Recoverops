"""Baseline classifier tests.

Two purposes:
  1. Confirm the deterministic rule engine is correct on obvious cases.
  2. Publish a floor accuracy on a synthetic batch so Gemini has to beat it.
"""
from __future__ import annotations

from recoverops.data.generator import GeneratorConfig, generate_batch
from recoverops.reasoning.rules import RuleBasedDiagnoser
from recoverops.reasoning.signals import signals_from_record
from recoverops.taxonomy import RootCause


def test_error_code_maps_to_cause_directly() -> None:
    from recoverops.models import AtRiskRecord
    from recoverops.taxonomy import RecordType
    from datetime import datetime, timezone

    diag = RuleBasedDiagnoser()
    rec = AtRiskRecord(
        record_id="r",
        record_type=RecordType.FAILED_PAYMENT,
        merchant_id="m",
        customer_id="c",
        amount_paise=100,
        error_code="BAD_REQUEST_ERROR:insufficient_funds",
        created_at=datetime.now(timezone.utc),
    )
    d = diag.diagnose(signals_from_record(rec))
    assert d.root_cause is RootCause.INSUFFICIENT_FUNDS
    assert d.confidence >= 0.8
    assert "error_code" in d.signals_used


def test_risk_flags_dominate_error_code() -> None:
    """Fraud signals must override any error-code mapping — no chasing fraud."""
    from recoverops.models import AtRiskRecord
    from recoverops.taxonomy import RecordType
    from datetime import datetime, timezone

    diag = RuleBasedDiagnoser()
    rec = AtRiskRecord(
        record_id="r",
        record_type=RecordType.FAILED_PAYMENT,
        merchant_id="m",
        customer_id="c",
        amount_paise=100,
        error_code="BAD_REQUEST_ERROR:insufficient_funds",
        risk_flags=["velocity_spike"],
        created_at=datetime.now(timezone.utc),
    )
    d = diag.diagnose(signals_from_record(rec))
    assert d.root_cause is RootCause.FRAUD_SUSPECTED


def test_rules_beat_the_floor_on_dev_batch() -> None:
    """Baseline: rule engine hits >=70% accuracy vs ground truth on 200 records."""
    diag = RuleBasedDiagnoser()
    records = list(generate_batch(GeneratorConfig(seed=42, size=200, split_name="dev")))
    correct = 0
    for rec in records:
        s = signals_from_record(rec)
        pred = diag.diagnose(s).root_cause
        if pred == rec.true_root_cause:
            correct += 1
    accuracy = correct / len(records)
    assert accuracy >= 0.70, f"rule-engine accuracy dropped to {accuracy:.2%}"


def test_diagnosis_record_id_matches_input() -> None:
    diag = RuleBasedDiagnoser()
    records = list(generate_batch(GeneratorConfig(seed=1, size=10, split_name="dev")))
    for rec in records:
        s = signals_from_record(rec)
        d = diag.diagnose(s)
        assert d.record_id == rec.record_id
