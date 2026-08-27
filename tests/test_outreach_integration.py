"""End-to-end: Hinglish drafter + promise store wired to the agent."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from recoverops.agent.loop import RecoveryAgent
from recoverops.config import load_guardrails
from recoverops.data.generator import GeneratorConfig, generate_batch
from recoverops.execution.mock import MockExecutor
from recoverops.outreach.hinglish import TemplateHinglishDrafter
from recoverops.outreach.promises import PromiseToPayStore
from recoverops.policy.engine import PolicyEngine
from recoverops.policy.planner import DeterministicPlanner
from recoverops.policy.store import IdempotencyStore
from recoverops.reasoning.rules import RuleBasedDiagnoser
from recoverops.taxonomy import RootCause


NOW = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


def _build_agent(promise_path: Path, drafter=None):
    g = load_guardrails()
    store = IdempotencyStore(ttl_hours=g.idempotency.key_ttl_hours)
    promises = PromiseToPayStore(promise_path)
    agent = RecoveryAgent(
        diagnoser=RuleBasedDiagnoser(),
        planner=DeterministicPlanner(g),
        engine=PolicyEngine(g),
        executor=MockExecutor(store=store, seed=42),
        guardrails=g,
        now_fn=lambda: NOW,
        hinglish_drafter=drafter or TemplateHinglishDrafter(),
        promise_store=promises,
    )
    return agent, promises


def _recent_b2b(records, now=NOW, days=20):
    return [
        r
        for r in records
        if r.true_root_cause is RootCause.B2B_OVERDUE
        and (now - r.created_at).days < days
    ]


def test_every_recent_b2b_overdue_record_captures_a_promise(tmp_path: Path) -> None:
    """For b2b records within the wallclock window, a promise must be
    captured. Older records are legitimately blocked by policy before
    outreach fires."""
    agent, promises = _build_agent(tmp_path / "promises.jsonl")
    records = list(generate_batch(GeneratorConfig(seed=42, size=300, split_name="dev")))
    b2b = _recent_b2b(records)
    assert b2b, "need at least one recent b2b record"
    agent.run_batch(b2b)

    captured = promises.all()
    assert len(captured) == len(b2b)
    for p in captured:
        assert p.language == "hinglish"
        assert p.channel == "whatsapp"
        assert p.status == "open"


def test_non_b2b_records_capture_no_promises(tmp_path: Path) -> None:
    agent, promises = _build_agent(tmp_path / "promises.jsonl")
    records = [
        r
        for r in generate_batch(GeneratorConfig(seed=42, size=100, split_name="dev"))
        if r.true_root_cause is not RootCause.B2B_OVERDUE
    ]
    agent.run_batch(records)
    assert promises.count() == 0


def test_outreach_drafted_event_is_emitted(tmp_path: Path) -> None:
    events: list[tuple[str, dict]] = []
    agent, _ = _build_agent(tmp_path / "promises.jsonl")
    agent._on_event = lambda stage, payload: events.append((stage, payload))
    records = list(generate_batch(GeneratorConfig(seed=42, size=200, split_name="dev")))
    recent = _recent_b2b(records)
    assert recent, "need at least one recent b2b record"
    agent.run_batch(recent[:1])

    outreach = [e for e in events if e[0] == "outreach_drafted"]
    assert outreach, "expected outreach_drafted event"
    payload = outreach[0][1]
    assert "message" in payload
    assert "Team RecoverOps" in payload["message"]
    assert "promise" in payload
