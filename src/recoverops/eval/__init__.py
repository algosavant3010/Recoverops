"""Evaluation harness — baselines, metrics, and the honest exceptions list."""

from .baselines import NaiveRetry3xBaseline, NoOpBaseline
from .harness import evaluate_all, write_report
from .metrics import StrategyResult, build_confusion, per_cause_metrics
from .oracle import GroundTruthOracle, appropriate_actions_for_cause

__all__ = [
    "GroundTruthOracle",
    "NaiveRetry3xBaseline",
    "NoOpBaseline",
    "StrategyResult",
    "appropriate_actions_for_cause",
    "build_confusion",
    "evaluate_all",
    "per_cause_metrics",
    "write_report",
]
