"""Signals are the trust boundary. These tests prove no leakage."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from recoverops.data.generator import GeneratorConfig, generate_batch
from recoverops.reasoning.signals import RecordSignals, signals_from_record


def test_signals_never_carry_ground_truth() -> None:
    """The reasoning plane must not see `true_root_cause` or `true_recover_prob`."""
    forbidden = {"true_root_cause", "true_recover_prob"}
    fields = set(RecordSignals.model_fields.keys())
    assert fields.isdisjoint(forbidden), f"leak: {fields & forbidden}"


def test_signals_never_carry_customer_id() -> None:
    """PII field `customer_id` must not survive the redaction step."""
    fields = set(RecordSignals.model_fields.keys())
    assert "customer_id" not in fields


def test_signals_from_record_strips_ground_truth() -> None:
    for rec in generate_batch(GeneratorConfig(seed=3, size=25, split_name="dev")):
        assert rec.true_root_cause is not None
        signals = signals_from_record(rec)
        dumped = signals.model_dump(mode="json")
        assert "true_root_cause" not in dumped
        assert "true_recover_prob" not in dumped
        assert "customer_id" not in dumped


def test_signals_metadata_is_allow_listed() -> None:
    """Only `channel` and `city` should survive from metadata."""
    for rec in generate_batch(GeneratorConfig(seed=3, size=25, split_name="dev")):
        signals = signals_from_record(rec)
        assert set(signals.safe_metadata).issubset({"channel", "city"})


def test_hours_since_created_is_non_negative() -> None:
    rec = next(generate_batch(GeneratorConfig(seed=3, size=1, split_name="dev")))
    now = rec.created_at + timedelta(hours=5)
    s = signals_from_record(rec, now=now)
    assert s.hours_since_created >= 5.0 - 1e-6


def test_signals_handle_missing_last_attempt() -> None:
    from recoverops.models import AtRiskRecord
    from recoverops.taxonomy import RecordType

    rec = AtRiskRecord(
        record_id="r",
        record_type=RecordType.ABANDONED_CHECKOUT,
        merchant_id="m",
        customer_id="c",
        amount_paise=100,
        created_at=datetime.now(timezone.utc),
    )
    s = signals_from_record(rec)
    assert s.hours_since_last_attempt is None
    assert s.has_prior_attempt is False
