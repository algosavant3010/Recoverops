"""End-to-end demo: run the agent with an audit log, then replay from disk."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from recoverops.agent.loop import RecoveryAgent
from recoverops.config import load_guardrails
from recoverops.data.generator import read_jsonl
from recoverops.execution.mock import MockExecutor
from recoverops.observability.audit import AuditLog
from recoverops.observability.replay import replay_report
from recoverops.policy.engine import PolicyEngine
from recoverops.policy.planner import DeterministicPlanner
from recoverops.policy.store import IdempotencyStore
from recoverops.reasoning.rules import RuleBasedDiagnoser


def _inr(paise: int) -> str:
    return f"Rs. {paise/100:>12,.2f}"


def main() -> None:
    records = list(read_jsonl(Path("data/dev/batch.jsonl")))
    g = load_guardrails()
    store = IdempotencyStore(ttl_hours=g.idempotency.key_ttl_hours)
    now = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)

    log_path = Path("logs/dev_batch.jsonl")
    if log_path.exists():
        log_path.unlink()

    with AuditLog(log_path, run_id="run_dev_demo", now_fn=lambda: now) as audit:
        agent = RecoveryAgent(
            diagnoser=RuleBasedDiagnoser(),
            planner=DeterministicPlanner(g),
            engine=PolicyEngine(g),
            executor=MockExecutor(store=store, seed=42),
            guardrails=g,
            on_event=audit,
            now_fn=lambda: now,
        )
        original = agent.run_batch(records)

    replayed = replay_report(log_path)

    print("=" * 72)
    print(f"AUDIT LOG:  {log_path}  ({log_path.stat().st_size:,} bytes)")
    print("=" * 72)

    def _line(label: str, a: str, b: str, ok: bool) -> str:
        mark = "OK" if ok else "MISMATCH"
        return f"  {label:26s} live={a:>18s}  replay={b:>18s}   [{mark}]"

    metrics = [
        ("records_processed", original.records_processed, replayed.records_processed, str, str),
        ("total_at_risk", original.total_at_risk_paise, replayed.total_at_risk_paise, _inr, _inr),
        ("total_recovered", original.total_recovered_paise, replayed.total_recovered_paise, _inr, _inr),
        ("recovery_rate", f"{original.recovery_rate:.1%}", f"{replayed.recovery_rate:.1%}", str, str),
        ("actions_attempted", original.actions_attempted, replayed.actions_attempted, str, str),
        ("actions_blocked", original.actions_blocked, replayed.actions_blocked, str, str),
        ("duplicates_prevented", original.duplicates_prevented, replayed.duplicates_prevented, str, str),
    ]
    all_ok = True
    for label, a, b, fa, fb in metrics:
        ok = a == b
        all_ok = all_ok and ok
        print(_line(label, fa(a), fb(b), ok))

    ok_blocks = original.blocks_by_rule == replayed.blocks_by_rule
    ok_terms = original.terminal_by_reason == replayed.terminal_by_reason
    all_ok = all_ok and ok_blocks and ok_terms
    print(f"  {'blocks_by_rule':26s} live={str(sorted(original.blocks_by_rule.items())):>18s}"
          f"   [{'OK' if ok_blocks else 'MISMATCH'}]")
    print(f"  {'terminal_by_reason':26s} live={str(sorted(original.terminal_by_reason.items())):>18s}"
          f"   [{'OK' if ok_terms else 'MISMATCH'}]")

    print()
    print("=" * 72)
    print("VERDICT:  " + ("audit log is COMPLETE and REPLAYABLE" if all_ok
                          else "MISMATCH — audit log incomplete"))
    print("=" * 72)


if __name__ == "__main__":
    main()
