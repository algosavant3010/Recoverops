"""Contract tests for the typed domain models. Cheap, fast, catch drift."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from recoverops.models import AtRiskRecord, Diagnosis, InterventionPlan
from recoverops.taxonomy import ActionKind, RecordType, RootCause


def _valid_record(**overrides) -> AtRiskRecord:
    base = dict(
        record_id="rec_dev_000001",
        record_type=RecordType.FAILED_PAYMENT,
        merchant_id="acc_ABCD1234",
        customer_id="cust_9999999999",
        amount_paise=50_000,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return AtRiskRecord(**base)  # type: ignore[arg-type]


def test_at_risk_record_defaults_are_sane() -> None:
    rec = _valid_record()
    assert rec.currency == "INR"
    assert rec.attempts == 0
    assert rec.risk_flags == []
    assert rec.metadata == {}
    assert rec.true_root_cause is None


def test_negative_amount_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _valid_record(amount_paise=-1)


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AtRiskRecord(  # type: ignore[call-arg]
            record_id="x",
            record_type=RecordType.FAILED_PAYMENT,
            merchant_id="m",
            customer_id="c",
            amount_paise=1,
            created_at=datetime.now(timezone.utc),
            not_a_real_field=True,
        )


def test_currency_is_normalised_uppercase() -> None:
    rec = _valid_record(currency="inr")
    assert rec.currency == "INR"


def test_true_recover_prob_bounds() -> None:
    with pytest.raises(ValidationError):
        _valid_record(true_recover_prob=1.5)
    with pytest.raises(ValidationError):
        _valid_record(true_recover_prob=-0.1)
    rec = _valid_record(true_recover_prob=0.42)
    assert rec.true_recover_prob == 0.42


def test_diagnosis_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        Diagnosis(
            record_id="r",
            root_cause=RootCause.GATEWAY_DOWNTIME,
            confidence=1.5,
            reasoning="",
        )


def test_intervention_plan_roundtrip_json() -> None:
    plan = InterventionPlan(
        record_id="r",
        action=ActionKind.SMART_RETRY,
        params={"strategy": "salary_cycle"},
        proposed_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
        rationale="funds likely available on salary date",
    )
    dumped = plan.model_dump_json()
    reloaded = InterventionPlan.model_validate_json(dumped)
    assert reloaded == plan
