"""Deterministic outcome oracle for evaluation.

The oracle decides whether a proposed action *succeeds* on a given record,
using two ingredients:

  1. The record's ground-truth `true_root_cause` and `true_recover_prob`.
  2. Whether the proposed action is "appropriate" for that true cause.

An appropriate action inherits the record's baseline recovery probability;
an inappropriate action falls to a small tail probability (~5%) so wrong
diagnoses can occasionally recover by luck. Fraud never recovers.

Outcomes are memoised on `(record_id, action, attempt_no)` and driven by a
hash-based PRNG, so any strategy calling the oracle in any order gets the
same deterministic verdict for the same triple. This is what makes the
baselines and the agent directly comparable.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..models import AtRiskRecord, InterventionPlan
from ..taxonomy import ActionKind, RootCause

_WRONG_ACTION_PROB_FLOOR = 0.05  # tiny chance a wrong intervention still lands
_FRAUD_RECOVERY_PROB = 0.0       # never recover fraud


def appropriate_actions_for_cause() -> dict[RootCause, frozenset[ActionKind]]:
    """Which actions *plausibly* recover money for each true cause."""
    return {
        RootCause.INSUFFICIENT_FUNDS: frozenset({
            ActionKind.SMART_RETRY,
            ActionKind.NUDGE,
        }),
        RootCause.GATEWAY_DOWNTIME: frozenset({
            ActionKind.SMART_RETRY,
            ActionKind.SWITCH_METHOD,
        }),
        RootCause.EXPIRED_CARD: frozenset({
            ActionKind.NUDGE_UPDATE_METHOD,
            ActionKind.SWITCH_METHOD,
        }),
        RootCause.MANDATE_LAPSED: frozenset({
            ActionKind.REAUTH_MANDATE,
            ActionKind.NUDGE,
        }),
        RootCause.CHECKOUT_ABANDONED: frozenset({
            ActionKind.RECOVERY_LINK,
            ActionKind.NUDGE,
            ActionKind.SMALL_INCENTIVE,
        }),
        RootCause.B2B_OVERDUE: frozenset({
            ActionKind.HINGLISH_PROMISE_TO_PAY,
            ActionKind.NUDGE,
        }),
        RootCause.FRAUD_SUSPECTED: frozenset(),
        RootCause.UNKNOWN: frozenset(),
    }


@dataclass
class GroundTruthOracle:
    """A callable outcome oracle for `MockExecutor.outcome_oracle`."""

    records_by_id: dict[str, AtRiskRecord]
    seed: int = 2026

    def __post_init__(self) -> None:
        self._appropriate = appropriate_actions_for_cause()

    def __call__(
        self,
        plan: InterventionPlan,
        amount_paise: int,
        attempt_no: int,
    ) -> tuple[bool, int]:
        record = self.records_by_id.get(plan.record_id)
        if record is None or record.true_root_cause is None:
            return False, 0

        cause = record.true_root_cause
        if cause is RootCause.FRAUD_SUSPECTED:
            return False, 0

        base = float(record.true_recover_prob or 0.0)
        if plan.action in self._appropriate.get(cause, frozenset()):
            prob = base
        else:
            prob = _WRONG_ACTION_PROB_FLOOR

        success = self._hit(plan.record_id, plan.action, attempt_no, prob)
        return (success, amount_paise if success else 0)

    def _hit(self, record_id: str, action: ActionKind, attempt: int, prob: float) -> bool:
        payload = f"{self.seed}|{record_id}|{action.value}|{attempt}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        u = int.from_bytes(digest[:8], "big") / (1 << 64)
        return u < prob
