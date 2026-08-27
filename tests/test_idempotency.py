"""Idempotency store — the anti-double-charge guarantee."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from recoverops.policy.keys import make_idempotency_key
from recoverops.policy.store import IdempotencyStore
from recoverops.taxonomy import ActionKind


def test_first_reserve_wins() -> None:
    store = IdempotencyStore(ttl_hours=1)
    key = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 1)
    assert store.check_and_reserve(key) is True
    assert store.check_and_reserve(key) is False


def test_same_triple_produces_same_key() -> None:
    a = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 1)
    b = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 1)
    assert a == b


def test_different_attempts_produce_different_keys() -> None:
    a = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 1)
    b = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 2)
    assert a != b


def test_different_actions_produce_different_keys() -> None:
    a = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 1)
    b = make_idempotency_key("rec_1", ActionKind.NUDGE, 1)
    assert a != b


def test_ttl_expiry_reclaims_key() -> None:
    clock = [datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)]

    def now() -> datetime:
        return clock[0]

    store = IdempotencyStore(ttl_hours=1, now_fn=now)
    key = make_idempotency_key("rec_1", ActionKind.SMART_RETRY, 1)
    assert store.check_and_reserve(key) is True
    # Advance past TTL — key must be reclaimable.
    clock[0] = clock[0] + timedelta(hours=2)
    assert store.check_and_reserve(key) is True


def test_size_reflects_active_reservations() -> None:
    store = IdempotencyStore(ttl_hours=1)
    assert store.size() == 0
    store.check_and_reserve(make_idempotency_key("r", ActionKind.SMART_RETRY, 1))
    store.check_and_reserve(make_idempotency_key("r", ActionKind.SMART_RETRY, 2))
    assert store.size() == 2
