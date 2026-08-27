"""Recovery agent loop.

For each at-risk record, this driver:
    1. Extracts observable signals (no ground-truth leak).
    2. Asks the diagnoser for a `Diagnosis`.
    3. Asks the planner for an `InterventionPlan` proposal.
    4. Asks the policy engine for a `PolicyDecision`.
    5. If allowed, calls the executor with the idempotency key.
    6. Updates the `RecordState`.
    7. Loops until terminal, capped, or out of attempts.

Nothing here decides money by itself — every rupee action goes through
the policy engine. This class is a coordinator, not a policy-maker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

from ..config import Guardrails
from ..execution.base import Executor
from ..models import ActionResult, AtRiskRecord, PolicyDecision, PromiseToPay
from ..outreach.hinglish import HinglishDrafter, OutreachContext
from ..outreach.promises import PromiseToPayStore
from ..policy.engine import PolicyEngine
from ..policy.planner import DeterministicPlanner
from ..policy.state import RecordState
from ..reasoning.base import Diagnoser
from ..reasoning.signals import signals_from_record
from ..taxonomy import ActionKind


@dataclass
class RunReport:
    """Aggregates one batch's outcome. What we ship in the eval report."""

    records_processed: int = 0
    total_at_risk_paise: int = 0
    total_recovered_paise: int = 0
    actions_attempted: int = 0
    actions_blocked: int = 0
    duplicates_prevented: int = 0
    blocks_by_rule: dict[str, int] = field(default_factory=dict)
    terminal_by_reason: dict[str, int] = field(default_factory=dict)

    @property
    def recovery_rate(self) -> float:
        if self.total_at_risk_paise == 0:
            return 0.0
        return self.total_recovered_paise / self.total_at_risk_paise


class RecoveryAgent:
    """Composes the four planes into one driver."""

    def __init__(
        self,
        *,
        diagnoser: Diagnoser,
        planner: DeterministicPlanner,
        engine: PolicyEngine,
        executor: Executor,
        guardrails: Guardrails,
        on_event: Callable[[str, dict], None] | None = None,
        now_fn: Callable[[], datetime] | None = None,
        hinglish_drafter: HinglishDrafter | None = None,
        promise_store: PromiseToPayStore | None = None,
    ) -> None:
        self._diagnoser = diagnoser
        self._planner = planner
        self._engine = engine
        self._executor = executor
        self._g = guardrails
        self._on_event = on_event or (lambda stage, payload: None)
        self._now = now_fn or (lambda: datetime.now(timezone.utc))
        self._drafter = hinglish_drafter
        self._promises = promise_store

    def run_batch(self, records: list[AtRiskRecord]) -> RunReport:
        report = RunReport()
        for record in records:
            self._run_record(record, report)
        return report

    def run_one(self, record: AtRiskRecord) -> RecordState:
        report = RunReport()
        return self._run_record(record, report)

    def _run_record(self, record: AtRiskRecord, report: RunReport) -> RecordState:
        state = RecordState(record_id=record.record_id, first_seen=record.created_at)
        self._emit("ingest", {
            "record_id": record.record_id,
            "record_type": record.record_type.value,
            "amount_paise": record.amount_paise,
            "currency": record.currency,
        })
        signals = signals_from_record(record)
        diagnosis = self._diagnoser.diagnose(signals)
        self._emit("diagnose", {"record_id": record.record_id, "diagnosis": diagnosis.model_dump(mode="json")})

        report.records_processed += 1
        report.total_at_risk_paise += record.amount_paise

        max_actions_per_record = self._g.caps.max_total_actions_per_record
        while state.total_actions < max_actions_per_record and not state.is_terminal:
            now = self._now()
            plan = self._planner.plan(diagnosis, state, now)
            self._emit("plan", {"record_id": record.record_id, "plan": plan.model_dump(mode="json")})

            decision = self._engine.evaluate(plan, diagnosis, state, now)
            self._emit("gate", {"record_id": record.record_id, "decision": decision.model_dump(mode="json")})

            if not decision.allowed:
                report.actions_blocked += 1
                report.blocks_by_rule[decision.rule_fired] = (
                    report.blocks_by_rule.get(decision.rule_fired, 0) + 1
                )
                # A blocked action means we can't progress this record further
                # under the current diagnosis/state; escalate and stop.
                if state.terminal is None:
                    state.terminal = "escalated"
                break

            state.apply_decision(plan)
            self._maybe_hinglish_outreach(record, plan, now)
            result = self._executor.execute(
                plan,
                idempotency_key=decision.idempotency_key,
                amount_paise=record.amount_paise,
                attempt_no=state.total_actions,
            )
            self._emit("execute", {"record_id": record.record_id, "result": result.model_dump(mode="json")})

            if result.status == "duplicate":
                report.duplicates_prevented += 1

            report.actions_attempted += 1
            state.apply_result(result)

            if state.is_terminal:
                break

        report.total_recovered_paise += state.recovered_paise
        reason = state.terminal or "max_attempts"
        report.terminal_by_reason[reason] = report.terminal_by_reason.get(reason, 0) + 1
        self._emit("terminal", {
            "record_id": record.record_id,
            "reason": reason,
            "recovered_paise": state.recovered_paise,
            "total_actions": state.total_actions,
        })
        return state

    def _emit(self, stage: str, payload: dict) -> None:
        self._on_event(stage, payload)

    def _maybe_hinglish_outreach(
        self, record: AtRiskRecord, plan, now: datetime
    ) -> None:
        """For HINGLISH_PROMISE_TO_PAY actions, draft the message + capture
        a promise BEFORE the executor runs. The audit event carries the
        rendered text so the log alone can prove what was sent."""
        if plan.action is not ActionKind.HINGLISH_PROMISE_TO_PAY:
            return
        if self._drafter is None:
            return
        days_overdue = max(0, int((now - record.created_at).total_seconds() // 86400))
        ctx = OutreachContext(
            record_id=record.record_id,
            amount_paise=record.amount_paise,
            currency=record.currency,
            days_overdue=days_overdue,
        )
        drafted = self._drafter.draft(ctx)
        promised_date = now + timedelta(days=drafted.suggested_promise_days)
        promise = PromiseToPay(
            record_id=record.record_id,
            promised_date=promised_date,
            channel=drafted.channel,
            language=drafted.language,
            captured_at=now,
        )
        if self._promises is not None:
            self._promises.append(promise)
        self._emit(
            "outreach_drafted",
            {
                "record_id": record.record_id,
                "message": drafted.message,
                "suggested_promise_days": drafted.suggested_promise_days,
                "tone": drafted.tone,
                "channel": drafted.channel,
                "language": drafted.language,
                "drafter": self._drafter.name,
                "promise": promise.model_dump(mode="json"),
            },
        )
