"""Action classifications + idempotency-key derivation.

Idempotency keys are content-addressable: the same (record, action, attempt)
tuple always produces the same key, so a duplicate call is detectable even
across process restarts or replayed events.
"""
from __future__ import annotations

import hashlib

from ..taxonomy import ActionKind

RETRY_ACTIONS: frozenset[ActionKind] = frozenset({
    ActionKind.SMART_RETRY,
    ActionKind.SWITCH_METHOD,
    ActionKind.REAUTH_MANDATE,
    ActionKind.RECOVERY_LINK,
    ActionKind.SMALL_INCENTIVE,
})

NUDGE_ACTIONS: frozenset[ActionKind] = frozenset({
    ActionKind.NUDGE,
    ActionKind.NUDGE_UPDATE_METHOD,
})

OUTREACH_ACTIONS: frozenset[ActionKind] = frozenset({
    ActionKind.NUDGE,
    ActionKind.NUDGE_UPDATE_METHOD,
    ActionKind.RECOVERY_LINK,
    ActionKind.HINGLISH_PROMISE_TO_PAY,
})

TERMINAL_ACTIONS: frozenset[ActionKind] = frozenset({
    ActionKind.SKIP,
    ActionKind.ESCALATE,
})

# Actions that touch money and must be idempotency-protected.
MONEY_ACTIONS: frozenset[ActionKind] = frozenset({
    ActionKind.SMART_RETRY,
    ActionKind.SWITCH_METHOD,
    ActionKind.REAUTH_MANDATE,
    ActionKind.RECOVERY_LINK,
    ActionKind.SMALL_INCENTIVE,
})


def make_idempotency_key(record_id: str, action: ActionKind, attempt_no: int) -> str:
    """Deterministic key for one (record, action, attempt) triple."""
    payload = f"{record_id}|{action.value}|{attempt_no}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"idem_{digest}"
