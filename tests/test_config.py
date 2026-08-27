"""Validates the shipped guardrails.yaml. If this fails, policy is broken."""
from __future__ import annotations

from recoverops.config import load_guardrails
from recoverops.taxonomy import ActionKind, RootCause


def test_default_guardrails_load() -> None:
    g = load_guardrails()
    assert g.version >= 1
    assert g.seed == 42


def test_every_root_cause_has_an_intervention_policy() -> None:
    """Coverage invariant: no diagnosis can fall through the policy engine."""
    g = load_guardrails()
    missing = [c for c in RootCause if c not in g.interventions]
    assert missing == [], f"missing intervention policy for: {missing}"


def test_allowed_actions_are_from_the_closed_set() -> None:
    g = load_guardrails()
    for cause, policy in g.interventions.items():
        for action in policy.actions:
            assert isinstance(action, ActionKind), (cause, action)


def test_caps_are_non_negative() -> None:
    g = load_guardrails()
    assert g.caps.max_retries_per_record >= 0
    assert g.caps.max_nudges_per_record >= 0
    assert 0 <= g.caps.max_discount_pct <= 100


def test_fraud_cause_never_authorises_money_actions() -> None:
    """Anti-vibecoded: an LLM must not be able to fund-chase a suspected fraud."""
    g = load_guardrails()
    fraud_actions = set(g.interventions[RootCause.FRAUD_SUSPECTED].actions)
    money_actions = {
        ActionKind.SMART_RETRY,
        ActionKind.SWITCH_METHOD,
        ActionKind.REAUTH_MANDATE,
        ActionKind.SMALL_INCENTIVE,
    }
    assert fraud_actions.isdisjoint(money_actions)
