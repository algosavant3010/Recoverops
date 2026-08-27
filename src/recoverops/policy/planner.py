"""Deterministic planner — picks an action for a diagnosis.

For now this is rule-based: it walks the `guardrails.interventions` list for
the diagnosed cause and returns the first action that is *eligible* given
the record's current state (e.g. don't propose another nudge if the nudge
cap is already hit).

This is intentionally boring. The LLM's judgment happens in the reasoning
plane (diagnosis). The planner is deterministic so the policy engine has
something predictable to gate. A smarter LLM-driven planner slots in later
behind the same interface without changing anything downstream.
"""
from __future__ import annotations

from datetime import datetime

from ..config import Guardrails
from ..models import Diagnosis, InterventionPlan
from ..taxonomy import ActionKind
from .keys import NUDGE_ACTIONS, RETRY_ACTIONS
from .state import RecordState


class DeterministicPlanner:
    """Chooses the highest-preference allowed action that hasn't been exhausted."""

    def __init__(self, guardrails: Guardrails) -> None:
        self._g = guardrails

    def plan(
        self,
        diagnosis: Diagnosis,
        state: RecordState,
        now: datetime,
    ) -> InterventionPlan:
        policy = self._g.interventions[diagnosis.root_cause]
        chosen = self._first_eligible(policy.actions, state)

        params: dict = {}
        strategy = policy.retry_strategy
        if chosen in RETRY_ACTIONS and strategy is not None:
            params["retry_strategy"] = strategy
        if chosen is ActionKind.SMALL_INCENTIVE and policy.incentive_max_pct is not None:
            params["max_discount_pct"] = policy.incentive_max_pct

        return InterventionPlan(
            record_id=state.record_id,
            action=chosen,
            params=params,
            proposed_at=now,
            rationale=f"policy for {diagnosis.root_cause.value}: chose {chosen.value}",
        )

    def _first_eligible(
        self, allowed: list[ActionKind], state: RecordState
    ) -> ActionKind:
        for action in allowed:
            if self._is_eligible(action, state):
                return action
        # Every option exhausted for this record — hand off to escalate.
        return ActionKind.ESCALATE

    def _is_eligible(self, action: ActionKind, state: RecordState) -> bool:
        if action in RETRY_ACTIONS and state.retries >= self._g.caps.max_retries_per_record:
            return False
        if action in NUDGE_ACTIONS and state.nudges >= self._g.caps.max_nudges_per_record:
            return False
        return True
