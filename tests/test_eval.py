"""Evaluation harness tests — determinism, baselines, and lift."""
from __future__ import annotations

from datetime import datetime, timezone

from recoverops.data.generator import GeneratorConfig, generate_batch
from recoverops.eval.baselines import NaiveRetry3xBaseline, NoOpBaseline
from recoverops.eval.harness import evaluate_all
from recoverops.eval.metrics import build_confusion, overall_accuracy, per_cause_metrics
from recoverops.eval.oracle import GroundTruthOracle
from recoverops.models import InterventionPlan
from recoverops.taxonomy import ActionKind, RootCause


def _load_batch(size: int = 100):
    return list(generate_batch(GeneratorConfig(seed=42, size=size, split_name="dev")))


def test_no_op_recovers_nothing() -> None:
    records = _load_batch(50)
    result = NoOpBaseline().run(records)
    assert result.total_recovered_paise == 0
    assert result.records_recovered == 0


def test_naive_retry_recovers_more_than_no_op() -> None:
    records = _load_batch(100)
    oracle = GroundTruthOracle(records_by_id={r.record_id: r for r in records})
    naive = NaiveRetry3xBaseline(oracle).run(records)
    assert naive.total_recovered_paise > 0


def test_recoverops_beats_naive_on_full_batch() -> None:
    """The headline claim of the pitch: RecoverOps > naive on both metrics."""
    records = _load_batch(200)
    report = evaluate_all(records)
    naive = next(s for s in report.strategies if s.name == "naive_retry_3x")
    ours = next(s for s in report.strategies if s.name == "recoverops")
    assert ours.total_recovered_paise > naive.total_recovered_paise
    assert ours.recovery_rate > naive.recovery_rate
    assert report.lift_over_naive_pp > 0


def test_evaluation_is_deterministic() -> None:
    records = _load_batch(100)
    a = evaluate_all(records)
    b = evaluate_all(records)
    for sa, sb in zip(a.strategies, b.strategies):
        assert sa.total_recovered_paise == sb.total_recovered_paise
        assert sa.records_recovered == sb.records_recovered


def test_oracle_never_recovers_fraud() -> None:
    records = _load_batch(500)
    fraud = [r for r in records if r.true_root_cause is RootCause.FRAUD_SUSPECTED]
    assert fraud, "need at least one fraud record for this test"
    oracle = GroundTruthOracle(records_by_id={r.record_id: r for r in records})
    for r in fraud:
        for action in ActionKind:
            plan = InterventionPlan(
                record_id=r.record_id,
                action=action,
                params={},
                proposed_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
                rationale="",
            )
            success, amount = oracle(plan, r.amount_paise, attempt_no=1)
            assert not success
            assert amount == 0


def test_oracle_is_deterministic_per_triple() -> None:
    records = _load_batch(20)
    oracle_a = GroundTruthOracle(records_by_id={r.record_id: r for r in records})
    oracle_b = GroundTruthOracle(records_by_id={r.record_id: r for r in records})
    r = records[0]
    plan = InterventionPlan(
        record_id=r.record_id,
        action=ActionKind.SMART_RETRY,
        params={},
        proposed_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
        rationale="",
    )
    outcomes_a = [oracle_a(plan, r.amount_paise, i) for i in range(1, 6)]
    outcomes_b = [oracle_b(plan, r.amount_paise, i) for i in range(1, 6)]
    assert outcomes_a == outcomes_b


def test_confusion_matrix_and_metrics() -> None:
    truths = [
        ("r1", RootCause.INSUFFICIENT_FUNDS),
        ("r2", RootCause.INSUFFICIENT_FUNDS),
        ("r3", RootCause.GATEWAY_DOWNTIME),
        ("r4", RootCause.GATEWAY_DOWNTIME),
    ]
    predictions = {
        "r1": RootCause.INSUFFICIENT_FUNDS,   # tp for insufficient
        "r2": RootCause.GATEWAY_DOWNTIME,     # fn for insufficient / fp for gateway
        "r3": RootCause.GATEWAY_DOWNTIME,     # tp for gateway
        "r4": RootCause.GATEWAY_DOWNTIME,     # tp for gateway
    }
    matrix = build_confusion(truths, predictions)
    assert matrix[RootCause.INSUFFICIENT_FUNDS][RootCause.INSUFFICIENT_FUNDS] == 1
    assert matrix[RootCause.INSUFFICIENT_FUNDS][RootCause.GATEWAY_DOWNTIME] == 1
    assert overall_accuracy(matrix) == 0.75

    m = per_cause_metrics(matrix)
    # gateway: tp=2, fp=1 (r2 misclassified as gateway), fn=0
    assert m[RootCause.GATEWAY_DOWNTIME]["precision"] == round(2/3, 4)
    assert m[RootCause.GATEWAY_DOWNTIME]["recall"] == 1.0


def test_exceptions_are_produced_and_bucketed() -> None:
    records = _load_batch(200)
    report = evaluate_all(records)
    assert report.exceptions, "expected some records to remain unrecovered"
    # Every fraud record must appear in exceptions as correctly skipped.
    fraud_records = [r for r in records if r.true_root_cause is RootCause.FRAUD_SUSPECTED]
    fraud_ex = [e for e in report.exceptions if e.true_cause == "fraud_suspected"]
    assert len(fraud_ex) == len(fraud_records)
    assert all(e.reason == "fraud_correctly_skipped" for e in fraud_ex)
