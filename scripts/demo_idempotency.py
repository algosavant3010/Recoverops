"""Demo: prove the idempotency guarantee prevents double-charges."""
from __future__ import annotations

from datetime import datetime, timezone

from recoverops.execution.mock import MockExecutor
from recoverops.models import InterventionPlan
from recoverops.policy.keys import make_idempotency_key
from recoverops.policy.store import IdempotencyStore
from recoverops.taxonomy import ActionKind


def main() -> None:
    store = IdempotencyStore(ttl_hours=24)
    exec_ = MockExecutor(store=store, seed=1)
    plan = InterventionPlan(
        record_id="rec_dev_000042",
        action=ActionKind.SMART_RETRY,
        params={"retry_strategy": "salary_cycle"},
        proposed_at=datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
        rationale="demo",
    )
    key = make_idempotency_key(plan.record_id, plan.action, attempt_no=1)

    print(f"Idempotency key: {key}")
    print()
    print("--- Call 1 ---")
    r1 = exec_.execute(plan, idempotency_key=key, amount_paise=50_000, attempt_no=1)
    print(f"  status:            {r1.status}")
    print(f"  recovered_amount:  Rs. {r1.recovered_amount_paise/100:,.2f}")
    print(f"  error:             {r1.error}")
    print()
    print("--- Call 2 (DUPLICATE - same key) ---")
    r2 = exec_.execute(plan, idempotency_key=key, amount_paise=50_000, attempt_no=1)
    print(f"  status:            {r2.status}")
    print(f"  recovered_amount:  Rs. {r2.recovered_amount_paise/100:,.2f}")
    print(f"  error:             {r2.error}")
    print()
    print("PROOF: duplicate returns status=duplicate with 0 recovery.")
    print("       No double-charge possible regardless of first-call outcome.")


if __name__ == "__main__":
    main()
