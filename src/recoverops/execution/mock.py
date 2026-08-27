"""In-process mock executor.

Two modes:
  1. Default — success/failure decided by a seeded PRNG using per-action
     baseline success rates. Fully deterministic given a seed.
  2. Oracle mode — the caller supplies an `outcome_oracle` callable that
     decides success and recovered amount. The evaluation harness uses this
     to derive outcomes from ground-truth `true_recover_prob` and the
     "was the intervention right for the true cause?" check.

Every executor call is idempotency-checked against a shared `IdempotencyStore`
before any side effects, so a duplicate key returns status="duplicate"
without recovering anything. This is the anti-double-charge guarantee.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Callable

from ..models import ActionResult, InterventionPlan
from ..policy.store import IdempotencyStore
from ..taxonomy import ActionKind

OutcomeOracle = Callable[[InterventionPlan, int, int], tuple[bool, int]]


def default_success_rates() -> dict[ActionKind, float]:
    """Baseline rates — deliberately modest so the demo isn't magical."""
    return {
        ActionKind.SMART_RETRY: 0.40,
        ActionKind.SWITCH_METHOD: 0.35,
        ActionKind.NUDGE: 0.15,
        ActionKind.NUDGE_UPDATE_METHOD: 0.25,
        ActionKind.REAUTH_MANDATE: 0.55,
        ActionKind.RECOVERY_LINK: 0.30,
        ActionKind.SMALL_INCENTIVE: 0.45,
        ActionKind.HINGLISH_PROMISE_TO_PAY: 0.55,
        ActionKind.SKIP: 0.0,
        ActionKind.ESCALATE: 0.0,
    }


class MockExecutor:
    """Deterministic simulated executor. Enforces idempotency in-line."""

    name = "mock_v1"

    def __init__(
        self,
        store: IdempotencyStore,
        *,
        seed: int = 0,
        success_rates: dict[ActionKind, float] | None = None,
        outcome_oracle: OutcomeOracle | None = None,
        latency_ms_range: tuple[int, int] = (30, 400),
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._rng = random.Random(seed)
        rates = default_success_rates()
        if success_rates:
            rates.update(success_rates)
        self._rates = rates
        self._oracle = outcome_oracle
        self._lat_lo, self._lat_hi = latency_ms_range
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def execute(
        self,
        plan: InterventionPlan,
        *,
        idempotency_key: str,
        amount_paise: int,
        attempt_no: int,
    ) -> ActionResult:
        # Atomic reserve. If the key is already claimed, do nothing — this
        # is the belt-and-braces defense against double-execution.
        if not self._store.check_and_reserve(idempotency_key):
            return self._result(
                plan=plan,
                idempotency_key=idempotency_key,
                attempt_no=attempt_no,
                status="duplicate",
                recovered=0,
                error="idempotency_key_reused",
            )

        if self._oracle is not None:
            success, recovered = self._oracle(plan, amount_paise, attempt_no)
        else:
            rate = self._rates.get(plan.action, 0.0)
            success = self._rng.random() < rate
            recovered = amount_paise if success else 0

        return self._result(
            plan=plan,
            idempotency_key=idempotency_key,
            attempt_no=attempt_no,
            status="success" if success else "failure",
            recovered=recovered,
        )

    def _result(
        self,
        *,
        plan: InterventionPlan,
        idempotency_key: str,
        attempt_no: int,
        status: str,
        recovered: int,
        error: str | None = None,
    ) -> ActionResult:
        return ActionResult(
            record_id=plan.record_id,
            idempotency_key=idempotency_key,
            action=plan.action,
            attempt_no=attempt_no,
            status=status,
            recovered_amount_paise=recovered,
            error=error,
            executed_at=self._now(),
            latency_ms=self._rng.randint(self._lat_lo, self._lat_hi),
        )
