"""Metrics — the numbers we publish. All computed on the held-out batch."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from ..taxonomy import RootCause


@dataclass
class StrategyResult:
    """The publishable outcome of one strategy on one batch."""

    name: str
    records_processed: int
    total_at_risk_paise: int
    total_recovered_paise: int
    records_recovered: int
    actions_taken: int
    unrecovered_count_by_reason: dict[str, int] = field(default_factory=dict)
    unrecovered_amount_by_reason: dict[str, int] = field(default_factory=dict)

    @property
    def recovery_rate(self) -> float:
        if self.total_at_risk_paise == 0:
            return 0.0
        return self.total_recovered_paise / self.total_at_risk_paise

    @property
    def record_recovery_rate(self) -> float:
        if self.records_processed == 0:
            return 0.0
        return self.records_recovered / self.records_processed

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "records_processed": self.records_processed,
            "records_recovered": self.records_recovered,
            "total_at_risk_paise": self.total_at_risk_paise,
            "total_recovered_paise": self.total_recovered_paise,
            "recovery_rate": round(self.recovery_rate, 4),
            "record_recovery_rate": round(self.record_recovery_rate, 4),
            "actions_taken": self.actions_taken,
            "unrecovered_count_by_reason": self.unrecovered_count_by_reason,
            "unrecovered_amount_by_reason": self.unrecovered_amount_by_reason,
        }


def build_confusion(
    truths: Iterable[tuple[str, RootCause]],
    predictions: dict[str, RootCause],
) -> dict[RootCause, dict[RootCause, int]]:
    """Row = true cause, column = predicted cause."""
    matrix: dict[RootCause, dict[RootCause, int]] = defaultdict(lambda: defaultdict(int))
    for record_id, truth in truths:
        pred = predictions.get(record_id)
        if pred is None:
            continue
        matrix[truth][pred] += 1
    return {k: dict(v) for k, v in matrix.items()}


def per_cause_metrics(
    matrix: dict[RootCause, dict[RootCause, int]],
) -> dict[RootCause, dict[str, float]]:
    """Precision, recall, F1 per class. Zero-safe."""
    labels: set[RootCause] = set(matrix.keys())
    for row in matrix.values():
        labels.update(row.keys())

    out: dict[RootCause, dict[str, float]] = {}
    for c in labels:
        tp = matrix.get(c, {}).get(c, 0)
        fp = sum(matrix.get(t, {}).get(c, 0) for t in labels if t != c)
        fn = sum(matrix.get(c, {}).get(p, 0) for p in labels if p != c)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        support = sum(matrix.get(c, {}).values())
        out[c] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    return out


def overall_accuracy(matrix: dict[RootCause, dict[RootCause, int]]) -> float:
    total = sum(sum(row.values()) for row in matrix.values())
    if total == 0:
        return 0.0
    correct = sum(matrix.get(c, {}).get(c, 0) for c in matrix)
    return correct / total


def lift_pp(base_rate: float, our_rate: float) -> float:
    """Signed absolute-percentage-point lift over a baseline."""
    return round((our_rate - base_rate) * 100, 2)
