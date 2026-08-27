"""Per-record execution state.

`RecordState` is a mutable projection of everything the policy engine needs
to make its next decision: what's been tried, when, how many times, and
whether the record has reached a terminal outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from ..models import ActionResult, InterventionPlan
from ..taxonomy import ActionKind
from .keys import NUDGE_ACTIONS, RETRY_ACTIONS, TERMINAL_ACTIONS

Terminal = Literal[
    "recovered",
    "escalated",
    "skipped",
    "max_attempts",
    "customer_optout",
    "fraud_stopped",
    "wallclock_expired",
]


@dataclass
class RecordState:
    """Everything the policy engine needs to know about a record's history."""

    record_id: str
    first_seen: datetime
    retries: int = 0
    nudges: int = 0
    total_actions: int = 0
    recovered_paise: int = 0
    terminal: Terminal | None = None
    last_action_at: dict[ActionKind, datetime] = field(default_factory=dict)
    history: list[ActionResult] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.terminal is not None

    @property
    def next_attempt_no(self) -> int:
        return self.total_actions + 1

    def apply_decision(self, plan: InterventionPlan) -> None:
        """Called for every attempted action, before the executor runs."""
        self.last_action_at[plan.action] = plan.proposed_at
        self.total_actions += 1
        if plan.action in RETRY_ACTIONS:
            self.retries += 1
        if plan.action in NUDGE_ACTIONS:
            self.nudges += 1
        if plan.action in TERMINAL_ACTIONS:
            self.terminal = "escalated" if plan.action is ActionKind.ESCALATE else "skipped"

    def apply_result(self, result: ActionResult) -> None:
        """Called after the executor returns."""
        self.history.append(result)
        if result.status == "success" and result.recovered_amount_paise > 0:
            self.recovered_paise += result.recovered_amount_paise
            self.terminal = "recovered"
