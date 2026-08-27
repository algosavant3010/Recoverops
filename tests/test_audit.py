"""Audit-log correctness + replay-round-trip tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from recoverops.agent.loop import RecoveryAgent
from recoverops.config import load_guardrails
from recoverops.data.generator import GeneratorConfig, generate_batch
from recoverops.execution.mock import MockExecutor
from recoverops.observability.audit import AuditLog, read_events
from recoverops.observability.replay import replay_report
from recoverops.policy.engine import PolicyEngine
from recoverops.policy.planner import DeterministicPlanner
from recoverops.policy.store import IdempotencyStore
from recoverops.reasoning.rules import RuleBasedDiagnoser


NOW = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


def _build_agent_with_log(path: Path, seed: int = 7):
    g = load_guardrails()
    store = IdempotencyStore(ttl_hours=g.idempotency.key_ttl_hours)
    audit = AuditLog(path, run_id="run_test_0001", now_fn=lambda: NOW)
    agent = RecoveryAgent(
        diagnoser=RuleBasedDiagnoser(),
        planner=DeterministicPlanner(g),
        engine=PolicyEngine(g),
        executor=MockExecutor(store=store, seed=seed),
        guardrails=g,
        on_event=audit,
        now_fn=lambda: NOW,
    )
    return agent, audit


def test_emit_writes_valid_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    with AuditLog(log_path, run_id="run_test", now_fn=lambda: NOW) as audit:
        audit.emit("ingest", {"record_id": "r1", "amount_paise": 100})
        audit.emit("diagnose", {"record_id": "r1", "diagnosis": {"root_cause": "unknown"}})

    events = read_events(log_path)
    assert len(events) == 2
    for e in events:
        assert set(e.keys()) >= {"run_id", "trace_id", "record_id", "stage", "ts", "payload"}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        json.loads(line)  # strict — every line must be valid JSON


def test_trace_id_is_stable_per_record(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    with AuditLog(log_path, run_id="run_test", now_fn=lambda: NOW) as audit:
        audit.emit("ingest", {"record_id": "r1", "amount_paise": 100})
        audit.emit("diagnose", {"record_id": "r1"})
        audit.emit("ingest", {"record_id": "r2", "amount_paise": 200})

    events = read_events(log_path)
    r1_traces = {e["trace_id"] for e in events if e["record_id"] == "r1"}
    r2_traces = {e["trace_id"] for e in events if e["record_id"] == "r2"}
    assert len(r1_traces) == 1
    assert len(r2_traces) == 1
    assert r1_traces.isdisjoint(r2_traces)


def test_missing_record_id_raises(tmp_path: Path) -> None:
    with AuditLog(tmp_path / "log.jsonl", run_id="r", now_fn=lambda: NOW) as audit:
        with pytest.raises(ValueError):
            audit.emit("ingest", {"amount_paise": 100})


def test_rule_fired_is_promoted_for_gate_events(tmp_path: Path) -> None:
    with AuditLog(tmp_path / "log.jsonl", run_id="r", now_fn=lambda: NOW) as audit:
        audit.emit(
            "gate",
            {
                "record_id": "r1",
                "decision": {"allowed": False, "rule_fired": "cap_retries"},
            },
        )
    events = read_events(tmp_path / "log.jsonl")
    assert events[0]["rule_fired"] == "cap_retries"


def test_replay_reproduces_run_report(tmp_path: Path) -> None:
    """The single strongest observability guarantee: log is complete."""
    log_path = tmp_path / "log.jsonl"
    agent, audit = _build_agent_with_log(log_path, seed=7)
    records = list(generate_batch(GeneratorConfig(seed=42, size=50, split_name="dev")))
    original = agent.run_batch(records)
    audit.close()

    replayed = replay_report(log_path)

    assert replayed.records_processed == original.records_processed
    assert replayed.total_at_risk_paise == original.total_at_risk_paise
    assert replayed.total_recovered_paise == original.total_recovered_paise
    assert replayed.actions_attempted == original.actions_attempted
    assert replayed.actions_blocked == original.actions_blocked
    assert replayed.duplicates_prevented == original.duplicates_prevented
    assert replayed.blocks_by_rule == original.blocks_by_rule
    assert replayed.terminal_by_reason == original.terminal_by_reason


def test_every_record_gets_ingest_and_terminal(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    agent, audit = _build_agent_with_log(log_path)
    records = list(generate_batch(GeneratorConfig(seed=42, size=20, split_name="dev")))
    agent.run_batch(records)
    audit.close()

    events = read_events(log_path)
    ingest_ids = {e["record_id"] for e in events if e["stage"] == "ingest"}
    terminal_ids = {e["record_id"] for e in events if e["stage"] == "terminal"}
    expected = {r.record_id for r in records}
    assert ingest_ids == expected
    assert terminal_ids == expected


def test_audit_events_are_sorted_by_stage_within_a_record(tmp_path: Path) -> None:
    """First event per record is 'ingest', last is 'terminal'."""
    log_path = tmp_path / "log.jsonl"
    agent, audit = _build_agent_with_log(log_path)
    records = list(generate_batch(GeneratorConfig(seed=42, size=5, split_name="dev")))
    agent.run_batch(records)
    audit.close()

    events = read_events(log_path)
    by_record: dict[str, list[str]] = {}
    for e in events:
        by_record.setdefault(e["record_id"], []).append(e["stage"])
    for stages in by_record.values():
        assert stages[0] == "ingest", stages
        assert stages[-1] == "terminal", stages
