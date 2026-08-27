"""Baseline strategies for honest comparison.

  * `NoOpBaseline` — the strict lower bound. Do nothing. Prove that the
    dataset has real money at risk that won't recover on its own.
  * `NaiveRetry3xBaseline` — retry every failed payment / subscription up
    to 3 times, no diagnosis, no cause-aware routing. This is what most
    merchants do today, and it's what RecoverOps has to beat.

Both baselines call the *same* `GroundTruthOracle` used by the agent so
outcomes are directly comparable.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..models import AtRiskRecord, InterventionPlan
from ..taxonomy import ActionKind, RecordType
from .metrics import StrategyResult
from .oracle import GroundTruthOracle


_NOW = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


class NoOpBaseline:
    """Attempt no interventions. Records only recover organically (0% here)."""

    name = "no_op"

    def run(self, records: list[AtRiskRecord]) -> StrategyResult:
        total = sum(r.amount_paise for r in records)
        unrecovered_amt = {"no_intervention": total}
        unrecovered_cnt = {"no_intervention": len(records)}
        return StrategyResult(
            name=self.name,
            records_processed=len(records),
            total_at_risk_paise=total,
            total_recovered_paise=0,
            records_recovered=0,
            actions_taken=0,
            unrecovered_count_by_reason=unrecovered_cnt,
            unrecovered_amount_by_reason=unrecovered_amt,
        )


class NaiveRetry3xBaseline:
    """Retry-3x on any failed payment or subscription. Ignores everything else."""

    name = "naive_retry_3x"
    _RETRYABLE = frozenset({RecordType.FAILED_PAYMENT, RecordType.FAILED_SUBSCRIPTION})

    def __init__(self, oracle: GroundTruthOracle) -> None:
        self._oracle = oracle

    def run(self, records: list[AtRiskRecord]) -> StrategyResult:
        recovered_amt = 0
        recovered_cnt = 0
        actions = 0
        unrecovered_cnt: dict[str, int] = {}
        unrecovered_amt: dict[str, int] = {}

        for r in records:
            if r.record_type not in self._RETRYABLE:
                self._bump(unrecovered_cnt, unrecovered_amt, "unhandled_type", r)
                continue

            hit = False
            for attempt in (1, 2, 3):
                actions += 1
                plan = InterventionPlan(
                    record_id=r.record_id,
                    action=ActionKind.SMART_RETRY,
                    params={},
                    proposed_at=_NOW,
                    rationale="naive_retry_3x",
                )
                success, amount = self._oracle(plan, r.amount_paise, attempt)
                if success:
                    recovered_amt += amount
                    recovered_cnt += 1
                    hit = True
                    break
            if not hit:
                self._bump(unrecovered_cnt, unrecovered_amt, "retries_exhausted", r)

        return StrategyResult(
            name=self.name,
            records_processed=len(records),
            total_at_risk_paise=sum(r.amount_paise for r in records),
            total_recovered_paise=recovered_amt,
            records_recovered=recovered_cnt,
            actions_taken=actions,
            unrecovered_count_by_reason=unrecovered_cnt,
            unrecovered_amount_by_reason=unrecovered_amt,
        )

    @staticmethod
    def _bump(cnt: dict, amt: dict, key: str, r: AtRiskRecord) -> None:
        cnt[key] = cnt.get(key, 0) + 1
        amt[key] = amt.get(key, 0) + r.amount_paise
