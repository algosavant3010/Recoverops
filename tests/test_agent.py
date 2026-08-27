"""Mock executor + planner + agent-loop end-to-end tests."""
from __future__ import annotations

from datetime import datetime, timezone

from recoverops.agent.loop import RecoveryAgent
from recoverops.config import load_guardrails
from recoverops.data.generator import GeneratorConfig, generate_batch
from recoverops.execution.mock import MockExecutor
from recoverops.models import Diagnosis, InterventionPlan
from recoverops.policy.engine import PolicyEngine
from recoverops.policy.planner import DeterministicPlanner
from recoverops.policy.state import RecordState
from recoverops.policy.store import IdempotencyStore
from recoverops.reasoning.rules import RuleBasedDiagnoser
from recoverops.taxonomy import ActionKind, RootCause


def test_duplicate_key_returns_duplicate_without_recovering() -> None:
    """The single most important invariant: no double-charges, ever."""
    store = IdempotencyStore(ttl_hours=24)
    exec_ = MockExecutor(store=store, seed=1)
    plan = InterventionPlan(
        record_id="r",
        action=ActionKind.SMART_RETRY,
        params={},
        proposed_at=datetime.now(timezone.utc),
        rationale="",
    )
    key = "idem_test_duplicate"

    first = exec_.execute(plan, idempotency_key=key, amount_paise=10_000, attempt_no=1)
    second = exec_.execute(plan, idempotency_key=key, amount_paise=10_000, attempt_no=1)

    assert first.status in {"success", "failure"}
    assert second.status == "duplicate"
    assert second.recovered_amount_paise == 0


def test_deterministic_with_seed() -> None:
    def run_once() -> list[str]:
        store = IdempotencyStore(ttl_hours=24)
        exec_ = MockExecutor(store=store, seed=42)
        outcomes = []
        for i in range(20):
            plan = InterventionPlan(
                record_id=f"r_{i}",
                action=ActionKind.SMART_RETRY,
                params={},
                proposed_at=datetime.now(timezone.utc),
                rationale="",
            )
            r = exec_.execute(
                plan,
                idempotency_key=f"idem_{i}",
                amount_paise=1_000,
                attempt_no=1,
            )
            outcomes.append(r.status)
        return outcomes

    assert run_once() == run_once()


def test_planner_picks_first_allowed_action_for_cause() -> None:
    g = load_guardrails()
    planner = DeterministicPlanner(g)
    state = RecordState(record_id="r", first_seen=datetime.now(timezone.utc))
    diag = Diagnosis(record_id="r", root_cause=RootCause.INSUFFICIENT_FUNDS, confidence=0.9, reasoning="")
    plan = planner.plan(diag, state, datetime.now(timezone.utc))
    assert plan.action in g.interventions[RootCause.INSUFFICIENT_FUNDS].actions
    assert plan.action == g.interventions[RootCause.INSUFFICIENT_FUNDS].actions[0]


def test_planner_falls_back_to_escalate_when_exhausted() -> None:
    g = load_guardrails()
    planner = DeterministicPlanner(g)
    state = RecordState(record_id="r", first_seen=datetime.now(timezone.utc))
    state.retries = g.caps.max_retries_per_record
    state.nudges = g.caps.max_nudges_per_record
    diag = Diagnosis(record_id="r", root_cause=RootCause.INSUFFICIENT_FUNDS, confidence=0.9, reasoning="")
    plan = planner.plan(diag, state, datetime.now(timezone.utc))
    assert plan.action is ActionKind.ESCALATE


def _build_agent(seed: int = 7, use_gate_time=None):
    g = load_guardrails()
    store = IdempotencyStore(ttl_hours=g.idempotency.key_ttl_hours)
    now = use_gate_time or datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)
    return RecoveryAgent(
        diagnoser=RuleBasedDiagnoser(),
        planner=DeterministicPlanner(g),
        engine=PolicyEngine(g),
        executor=MockExecutor(store=store, seed=seed),
        guardrails=g,
        now_fn=lambda: now,
    ), store


def test_agent_recovers_some_money_on_dev_batch() -> None:
    agent, _ = _build_agent()
    records = list(generate_batch(GeneratorConfig(seed=42, size=50, split_name="dev")))
    report = agent.run_batch(records)

    assert report.records_processed == 50
    assert report.total_at_risk_paise > 0
    assert report.total_recovered_paise > 0
    assert 0.0 < report.recovery_rate < 1.0, f"unexpected rate {report.recovery_rate}"


def test_agent_never_touches_money_on_fraud_records() -> None:
    """End-to-end proof of the fraud-safety invariant."""
    agent, _ = _build_agent()
    records = [
        r
        for r in generate_batch(GeneratorConfig(seed=42, size=200, split_name="dev"))
        if r.true_root_cause is RootCause.FRAUD_SUSPECTED
    ]
    assert records, "need at least one fraud record for this test"
    report = agent.run_batch(records)
    assert report.total_recovered_paise == 0
    # Every fraud record should terminate as escalated or skipped, never recovered.
    assert "recovered" not in report.terminal_by_reason


def test_agent_events_are_emitted_in_expected_order() -> None:
    events: list[tuple[str, dict]] = []
    g = load_guardrails()
    store = IdempotencyStore(ttl_hours=1)
    agent = RecoveryAgent(
        diagnoser=RuleBasedDiagnoser(),
        planner=DeterministicPlanner(g),
        engine=PolicyEngine(g),
        executor=MockExecutor(store=store, seed=0),
        guardrails=g,
        on_event=lambda stage, payload: events.append((stage, payload)),
        now_fn=lambda: datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
    )
    record = next(iter(generate_batch(GeneratorConfig(seed=1, size=1, split_name="dev"))))
    agent.run_one(record)

    stages = [s for s, _ in events]
    assert stages[0] == "ingest"
    assert stages[1] == "diagnose"
    assert stages[-1] == "terminal"
    assert set(stages).issubset({"ingest", "diagnose", "plan", "gate", "execute", "terminal"})
    assert "plan" in stages
    assert "gate" in stages
