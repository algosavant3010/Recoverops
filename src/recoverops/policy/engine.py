"""Policy engine — the deterministic gate every rupee action must pass through.

Contract: given an `InterventionPlan` proposed upstream (by the LLM/planner),
a `Diagnosis` (for cause-action compatibility), and the record's current
`RecordState`, return a `PolicyDecision` explaining exactly why the action
was allowed or blocked.

Every rule fires with a *named* verdict, so the audit log can prove after
the fact which policy rule protected the money.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import Guardrails
from ..models import Diagnosis, InterventionPlan, PolicyDecision
from ..taxonomy import ActionKind
from .keys import (
    MONEY_ACTIONS,
    NUDGE_ACTIONS,
    OUTREACH_ACTIONS,
    RETRY_ACTIONS,
    make_idempotency_key,
)
from .state import RecordState


@dataclass(frozen=True)
class _Verdict:
    allowed: bool
    rule: str
    reason: str


class PolicyEngine:
    """Rules fire in a fixed order. First blocking rule wins."""

    def __init__(self, guardrails: Guardrails) -> None:
        self._g = guardrails

    def evaluate(
        self,
        plan: InterventionPlan,
        diagnosis: Diagnosis,
        state: RecordState,
        now: datetime,
    ) -> PolicyDecision:
        key = make_idempotency_key(plan.record_id, plan.action, state.next_attempt_no)
        v = self._first_blocker(plan, diagnosis, state, now)
        return PolicyDecision(
            record_id=plan.record_id,
            plan=plan,
            allowed=v.allowed,
            rule_fired=v.rule,
            idempotency_key=key,
            reason=v.reason,
        )

    def _first_blocker(
        self,
        plan: InterventionPlan,
        diagnosis: Diagnosis,
        state: RecordState,
        now: datetime,
    ) -> _Verdict:
        # 1. Terminal state — the record is done, no more actions.
        if state.is_terminal:
            return _Verdict(False, "terminal_state", f"record already {state.terminal}")

        # 2. Wallclock cap — stop chasing very old records.
        max_age = timedelta(days=self._g.stopping_rules.max_wallclock_days)
        if now - state.first_seen > max_age:
            return _Verdict(False, "wallclock_expired", f"older than {max_age.days} days")

        # 3. Action must be permitted for this diagnosed cause.
        allowed_for_cause = set(self._g.interventions[diagnosis.root_cause].actions)
        if plan.action not in allowed_for_cause:
            return _Verdict(
                False,
                "action_not_allowed_for_cause",
                f"{plan.action.value} not in policy for {diagnosis.root_cause.value}",
            )

        # 4. Batch/session caps.
        if state.total_actions >= self._g.caps.max_total_actions_per_record:
            return _Verdict(False, "cap_total_actions", "total-actions cap hit")

        if plan.action in RETRY_ACTIONS and state.retries >= self._g.caps.max_retries_per_record:
            return _Verdict(False, "cap_retries", "per-record retry cap hit")

        if plan.action in NUDGE_ACTIONS and state.nudges >= self._g.caps.max_nudges_per_record:
            return _Verdict(False, "cap_nudges", "per-record nudge cap hit")

        # 5. Discount caps — enforce the money-side of the small_incentive action.
        if plan.action is ActionKind.SMALL_INCENTIVE:
            proposed_pct = float(plan.params.get("max_discount_pct", 0))
            if proposed_pct > self._g.caps.max_discount_pct:
                return _Verdict(
                    False,
                    "cap_discount_pct",
                    f"discount {proposed_pct}% > max {self._g.caps.max_discount_pct}%",
                )

        # 6. Cooldowns — must not repeat the same action too soon.
        last = state.last_action_at.get(plan.action)
        if last is not None:
            cd = self._cooldown_for(plan.action)
            if cd is not None and now - last < cd:
                return _Verdict(False, "cooldown_active", f"{plan.action.value} on cooldown")

        # 7. Quiet hours for outreach.
        if plan.action in OUTREACH_ACTIONS and self._in_quiet_hours(now):
            return _Verdict(False, "quiet_hours", "outreach blocked during quiet hours")

        # 8. Money-touching actions require an idempotency key (always true by
        #    construction, but a paranoid check documents the invariant).
        if plan.action in MONEY_ACTIONS and not plan.record_id:
            return _Verdict(False, "missing_record_id", "money action needs record id")

        return _Verdict(True, "allowed", "all policy rules passed")

    def _cooldown_for(self, action: ActionKind) -> timedelta | None:
        c = self._g.cooldowns
        if action in RETRY_ACTIONS:
            return timedelta(hours=c.retry_hours)
        if action in NUDGE_ACTIONS:
            return timedelta(hours=c.nudge_hours)
        if action in OUTREACH_ACTIONS:
            return timedelta(hours=c.outreach_hours)
        return None

    def _in_quiet_hours(self, now: datetime) -> bool:
        q = self._g.outreach.quiet_hours_local
        h = now.hour
        # Window wraps midnight (e.g. 21..09).
        if q.start_hour <= q.end_hour:
            return q.start_hour <= h < q.end_hour
        return h >= q.start_hour or h < q.end_hour
