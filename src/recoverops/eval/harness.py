"""Evaluation harness — runs the three strategies and writes the report.

Strategies:
  1. `no_op`           — do nothing; lower bound.
  2. `naive_retry_3x`  — retry-3x on failed payments/subscriptions.
  3. `recoverops`      — full agent (rule-based diagnoser + policy engine).

All three consume the same `GroundTruthOracle`, so outcome differences come
from strategy quality, not from randomness.

The harness also computes the diagnosis confusion matrix for the agent and
produces an honest exceptions list — the records we did *not* recover, and
why.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..agent.loop import RecoveryAgent
from ..config import load_guardrails
from ..execution.mock import MockExecutor
from ..models import AtRiskRecord
from ..policy.engine import PolicyEngine
from ..policy.planner import DeterministicPlanner
from ..policy.state import RecordState
from ..policy.store import IdempotencyStore
from ..reasoning.rules import RuleBasedDiagnoser
from ..reasoning.signals import signals_from_record
from ..taxonomy import RootCause
from .baselines import NaiveRetry3xBaseline, NoOpBaseline
from .metrics import (
    StrategyResult,
    build_confusion,
    lift_pp,
    overall_accuracy,
    per_cause_metrics,
)
from .oracle import GroundTruthOracle

_NOW = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


@dataclass
class Exception_:  # `Exception` is a builtin — underscored to avoid shadow
    record_id: str
    record_type: str
    true_cause: str
    predicted_cause: str
    amount_paise: int
    reason: str


@dataclass
class EvalReport:
    strategies: list[StrategyResult]
    diagnosis_accuracy: float
    confusion_matrix: dict
    per_cause: dict
    exceptions: list[Exception_] = field(default_factory=list)
    lift_over_naive_pp: float = 0.0
    lift_over_no_op_pp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "strategies": [s.to_dict() for s in self.strategies],
            "diagnosis_accuracy": round(self.diagnosis_accuracy, 4),
            "confusion_matrix": {
                truth.value: {pred.value: n for pred, n in row.items()}
                for truth, row in self.confusion_matrix.items()
            },
            "per_cause": {
                cause.value: metrics for cause, metrics in self.per_cause.items()
            },
            "lift_over_naive_pp": self.lift_over_naive_pp,
            "lift_over_no_op_pp": self.lift_over_no_op_pp,
            "exceptions": [e.__dict__ for e in self.exceptions],
        }


def _run_recoverops(
    records: list[AtRiskRecord],
    oracle: GroundTruthOracle,
) -> tuple[StrategyResult, dict[str, RootCause], list[Exception_]]:
    g = load_guardrails()
    diagnoser = RuleBasedDiagnoser()
    predictions: dict[str, RootCause] = {}
    per_record_states: dict[str, RecordState] = {}

    def _remember_state(agent: RecoveryAgent, r: AtRiskRecord) -> RecordState:
        # We use run_one so we can capture the returned state directly.
        return agent.run_one(r)

    store = IdempotencyStore(ttl_hours=g.idempotency.key_ttl_hours)
    agent = RecoveryAgent(
        diagnoser=diagnoser,
        planner=DeterministicPlanner(g),
        engine=PolicyEngine(g),
        executor=MockExecutor(store=store, seed=42, outcome_oracle=oracle),
        guardrails=g,
        now_fn=lambda: _NOW,
    )

    recovered_amt = 0
    recovered_cnt = 0
    actions = 0
    unrecovered_cnt: dict[str, int] = {}
    unrecovered_amt: dict[str, int] = {}
    exceptions: list[Exception_] = []

    for r in records:
        signals = signals_from_record(r, now=_NOW)
        pred = diagnoser.diagnose(signals).root_cause
        predictions[r.record_id] = pred

        state = _remember_state(agent, r)
        per_record_states[r.record_id] = state
        actions += state.total_actions

        if state.recovered_paise > 0:
            recovered_amt += state.recovered_paise
            recovered_cnt += 1
            continue

        reason = _bucket_reason(r, pred, state.terminal)
        unrecovered_cnt[reason] = unrecovered_cnt.get(reason, 0) + 1
        unrecovered_amt[reason] = unrecovered_amt.get(reason, 0) + r.amount_paise
        exceptions.append(
            Exception_(
                record_id=r.record_id,
                record_type=r.record_type.value,
                true_cause=r.true_root_cause.value if r.true_root_cause else "n/a",
                predicted_cause=pred.value,
                amount_paise=r.amount_paise,
                reason=reason,
            )
        )

    result = StrategyResult(
        name="recoverops",
        records_processed=len(records),
        total_at_risk_paise=sum(r.amount_paise for r in records),
        total_recovered_paise=recovered_amt,
        records_recovered=recovered_cnt,
        actions_taken=actions,
        unrecovered_count_by_reason=unrecovered_cnt,
        unrecovered_amount_by_reason=unrecovered_amt,
    )
    return result, predictions, exceptions


def _bucket_reason(
    record: AtRiskRecord,
    pred_cause: RootCause,
    terminal: str | None,
) -> str:
    if record.true_root_cause is RootCause.FRAUD_SUSPECTED:
        return "fraud_correctly_skipped"
    if pred_cause != record.true_root_cause and pred_cause is not RootCause.UNKNOWN:
        return "misdiagnosis_led_to_wrong_action"
    if pred_cause is RootCause.UNKNOWN:
        return "unknown_diagnosis"
    if terminal in {"escalated", "max_attempts"}:
        return "exhausted_attempts_or_policy_block"
    return terminal or "other"


def evaluate_all(records: list[AtRiskRecord]) -> EvalReport:
    oracle = GroundTruthOracle(records_by_id={r.record_id: r for r in records})

    no_op = NoOpBaseline().run(records)
    naive = NaiveRetry3xBaseline(oracle).run(records)
    ours, predictions, exceptions = _run_recoverops(records, oracle)

    truths: list[tuple[str, RootCause]] = [
        (r.record_id, r.true_root_cause) for r in records if r.true_root_cause is not None
    ]
    confusion = build_confusion(truths, predictions)
    per_cause = per_cause_metrics(confusion)
    diag_acc = overall_accuracy(confusion)

    return EvalReport(
        strategies=[no_op, naive, ours],
        diagnosis_accuracy=diag_acc,
        confusion_matrix=confusion,
        per_cause=per_cause,
        exceptions=exceptions,
        lift_over_naive_pp=lift_pp(naive.recovery_rate, ours.recovery_rate),
        lift_over_no_op_pp=lift_pp(no_op.recovery_rate, ours.recovery_rate),
    )


def write_report(report: EvalReport, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "eval_report.json"
    md_path = out_dir / "eval_report.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _render_markdown(report: EvalReport) -> str:
    lines: list[str] = []
    lines.append("# RecoverOps evaluation")
    lines.append("")
    lines.append("## Strategy comparison")
    lines.append("")
    lines.append("| Strategy | Records recovered | Amount recovered | Recovery rate | Actions taken |")
    lines.append("|---|---:|---:|---:|---:|")
    for s in report.strategies:
        lines.append(
            f"| {s.name} | {s.records_recovered}/{s.records_processed} | "
            f"Rs. {s.total_recovered_paise/100:,.0f} | {s.recovery_rate:.1%} | {s.actions_taken} |"
        )
    lines.append("")
    lines.append(f"**Lift over `naive_retry_3x`:** {report.lift_over_naive_pp:+.2f} pp")
    lines.append("")
    lines.append(f"**Lift over `no_op`:** {report.lift_over_no_op_pp:+.2f} pp")
    lines.append("")
    lines.append("## Diagnosis confusion matrix (agent's rule-based diagnoser)")
    lines.append("")
    lines.append(f"**Overall accuracy:** {report.diagnosis_accuracy:.2%}")
    lines.append("")
    lines.append("| True cause | Precision | Recall | F1 | Support |")
    lines.append("|---|---:|---:|---:|---:|")
    for cause, metrics in sorted(report.per_cause.items(), key=lambda x: -x[1]["support"]):
        lines.append(
            f"| {cause.value} | {metrics['precision']:.2%} | {metrics['recall']:.2%} | "
            f"{metrics['f1']:.2%} | {metrics['support']} |"
        )
    lines.append("")
    lines.append("## Exceptions (records we did not recover)")
    lines.append("")
    if not report.exceptions:
        lines.append("_None — every record recovered._")
    else:
        buckets: dict[str, int] = {}
        buckets_amt: dict[str, int] = {}
        for e in report.exceptions:
            buckets[e.reason] = buckets.get(e.reason, 0) + 1
            buckets_amt[e.reason] = buckets_amt.get(e.reason, 0) + e.amount_paise
        lines.append("| Reason | Count | Amount |")
        lines.append("|---|---:|---:|")
        for reason, n in sorted(buckets.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {n} | Rs. {buckets_amt[reason]/100:,.0f} |")
    return "\n".join(lines) + "\n"
