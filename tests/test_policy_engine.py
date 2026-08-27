"""Policy engine — every rule verified independently."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from recoverops.config import load_guardrails
from recoverops.models import Diagnosis, InterventionPlan
from recoverops.policy.engine import PolicyEngine
from recoverops.policy.state import RecordState
from recoverops.taxonomy import ActionKind, RootCause


@pytest.fixture
def guardrails():
    return load_guardrails()


@pytest.fixture
def engine(guardrails):
    return PolicyEngine(guardrails)


NOW = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)  # 3 PM UTC → outside quiet hours


def _diagnosis(cause: RootCause = RootCause.INSUFFICIENT_FUNDS, conf: float = 0.9) -> Diagnosis:
    return Diagnosis(record_id="r", root_cause=cause, confidence=conf, reasoning="")


def _plan(action: ActionKind, **params) -> InterventionPlan:
    return InterventionPlan(
        record_id="r",
        action=action,
        params=params,
        proposed_at=NOW,
        rationale="",
    )


def _fresh_state() -> RecordState:
    return RecordState(record_id="r", first_seen=NOW - timedelta(hours=2))


def test_happy_path_allows_valid_retry(engine) -> None:
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), _fresh_state(), NOW)
    assert d.allowed
    assert d.rule_fired == "allowed"
    assert d.idempotency_key.startswith("idem_")


def test_terminal_state_blocks_everything(engine) -> None:
    state = _fresh_state()
    state.terminal = "recovered"
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), state, NOW)
    assert not d.allowed
    assert d.rule_fired == "terminal_state"


def test_wrong_action_for_cause_blocks(engine) -> None:
    # `reauth_mandate` is not a valid action for `insufficient_funds`.
    d = engine.evaluate(
        _plan(ActionKind.REAUTH_MANDATE),
        _diagnosis(RootCause.INSUFFICIENT_FUNDS),
        _fresh_state(),
        NOW,
    )
    assert not d.allowed
    assert d.rule_fired == "action_not_allowed_for_cause"


def test_fraud_cause_cannot_authorise_money_action(engine) -> None:
    """The single most important safety invariant."""
    for action in (ActionKind.SMART_RETRY, ActionKind.SWITCH_METHOD, ActionKind.SMALL_INCENTIVE):
        d = engine.evaluate(
            _plan(action),
            _diagnosis(RootCause.FRAUD_SUSPECTED),
            _fresh_state(),
            NOW,
        )
        assert not d.allowed, f"{action.value} should be blocked for fraud"


def test_retry_cap_blocks(engine, guardrails) -> None:
    state = _fresh_state()
    state.retries = guardrails.caps.max_retries_per_record
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), state, NOW)
    assert not d.allowed
    assert d.rule_fired == "cap_retries"


def test_nudge_cap_blocks(engine, guardrails) -> None:
    state = _fresh_state()
    state.nudges = guardrails.caps.max_nudges_per_record
    d = engine.evaluate(
        _plan(ActionKind.NUDGE),
        _diagnosis(RootCause.INSUFFICIENT_FUNDS),
        state,
        NOW,
    )
    assert not d.allowed
    assert d.rule_fired == "cap_nudges"


def test_total_actions_cap_blocks(engine, guardrails) -> None:
    state = _fresh_state()
    state.total_actions = guardrails.caps.max_total_actions_per_record
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), state, NOW)
    assert not d.allowed
    assert d.rule_fired == "cap_total_actions"


def test_wallclock_expiry_blocks(engine, guardrails) -> None:
    state = RecordState(
        record_id="r",
        first_seen=NOW - timedelta(days=guardrails.stopping_rules.max_wallclock_days + 1),
    )
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), state, NOW)
    assert not d.allowed
    assert d.rule_fired == "wallclock_expired"


def test_cooldown_blocks_retry(engine, guardrails) -> None:
    state = _fresh_state()
    # Last retry happened 1 hour ago — cooldown is 24h.
    state.last_action_at[ActionKind.SMART_RETRY] = NOW - timedelta(hours=1)
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), state, NOW)
    assert not d.allowed
    assert d.rule_fired == "cooldown_active"


def test_cooldown_lifts_after_window(engine, guardrails) -> None:
    state = _fresh_state()
    state.last_action_at[ActionKind.SMART_RETRY] = NOW - timedelta(
        hours=guardrails.cooldowns.retry_hours + 1
    )
    d = engine.evaluate(_plan(ActionKind.SMART_RETRY), _diagnosis(), state, NOW)
    assert d.allowed


def test_discount_cap_blocks(engine, guardrails) -> None:
    d = engine.evaluate(
        _plan(ActionKind.SMALL_INCENTIVE, max_discount_pct=guardrails.caps.max_discount_pct + 1),
        _diagnosis(RootCause.CHECKOUT_ABANDONED),
        _fresh_state(),
        NOW,
    )
    assert not d.allowed
    assert d.rule_fired == "cap_discount_pct"


def test_quiet_hours_block_outreach(engine) -> None:
    # 22:00 UTC falls into the 21..09 quiet window.
    late = datetime(2026, 8, 28, 22, 0, tzinfo=timezone.utc)
    d = engine.evaluate(
        _plan(ActionKind.NUDGE),
        _diagnosis(RootCause.INSUFFICIENT_FUNDS),
        _fresh_state(),
        late,
    )
    assert not d.allowed
    assert d.rule_fired == "quiet_hours"
