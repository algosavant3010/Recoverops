"""Executor protocol — one call site, many implementations."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import ActionResult, InterventionPlan


@runtime_checkable
class Executor(Protocol):
    """Executes an approved `InterventionPlan`. Must be idempotent per key."""

    name: str

    def execute(
        self,
        plan: InterventionPlan,
        *,
        idempotency_key: str,
        amount_paise: int,
        attempt_no: int,
    ) -> ActionResult:
        ...
