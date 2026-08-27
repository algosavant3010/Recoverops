"""Live demo: draft Hinglish promise-to-pay messages for real B2B records.

Runs the full agent on a handful of `b2b_overdue` records, capturing the
drafted messages + promises. Uses Gemini if a key is present, else the
template drafter. Either way, the demo always produces output.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from recoverops.agent.loop import RecoveryAgent
from recoverops.config import load_guardrails
from recoverops.data.generator import read_jsonl
from recoverops.execution.mock import MockExecutor
from recoverops.outreach.hinglish import (
    GeminiHinglishDrafter,
    TemplateHinglishDrafter,
    get_hinglish_drafter,
)
from recoverops.outreach.promises import PromiseToPayStore
from recoverops.policy.engine import PolicyEngine
from recoverops.policy.planner import DeterministicPlanner
from recoverops.policy.store import IdempotencyStore
from recoverops.reasoning.rules import RuleBasedDiagnoser
from recoverops.taxonomy import RootCause


NOW = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


def _pick_b2b(records, k=3):
    b2b = [
        r for r in records
        if r.true_root_cause is RootCause.B2B_OVERDUE
        and (NOW - r.created_at).days < 20
    ]
    return b2b[:k]


def _run_with_drafter(drafter, records, promises_path: Path) -> list[dict]:
    g = load_guardrails()
    store = IdempotencyStore(ttl_hours=g.idempotency.key_ttl_hours)
    promises = PromiseToPayStore(promises_path)
    promises.clear()

    events: list[dict] = []
    agent = RecoveryAgent(
        diagnoser=RuleBasedDiagnoser(),
        planner=DeterministicPlanner(g),
        engine=PolicyEngine(g),
        executor=MockExecutor(store=store, seed=42),
        guardrails=g,
        on_event=lambda stage, payload: (
            events.append(payload) if stage == "outreach_drafted" else None
        ),
        now_fn=lambda: NOW,
        hinglish_drafter=drafter,
        promise_store=promises,
    )
    agent.run_batch(records)
    return events


def _print(title: str, events: list[dict]) -> None:
    print("=" * 78)
    print(title)
    print("=" * 78)
    if not events:
        print("  (no outreach events emitted)")
        return
    for e in events:
        amount = e["promise"]["record_id"]
        print(f"\nRecord:            {e['record_id']}")
        print(f"Drafter:           {e['drafter']}")
        print(f"Tone:              {e['tone']}")
        print(f"Promise-by:        +{e['suggested_promise_days']} day(s)")
        print(f"Channel/Lang:      {e['channel']} / {e['language']}")
        print(f"Message:           {e['message']}")


def main() -> None:
    records = list(read_jsonl(Path("data/dev/batch.jsonl")))
    picks = _pick_b2b(records, k=3)
    if not picks:
        print("no b2b_overdue records found in the batch")
        return

    print(f"\nPicked {len(picks)} B2B overdue records:")
    for r in picks:
        print(f"  {r.record_id}   amount=Rs. {r.amount_paise/100:,.0f}   "
              f"days_overdue={(NOW - r.created_at).days}")

    # 1) Template drafter — always works, no API cost.
    template_events = _run_with_drafter(
        TemplateHinglishDrafter(), picks, Path("artifacts/promises_template.jsonl")
    )
    _print("TEMPLATE DRAFTER  (offline, deterministic)", template_events)

    # 2) Gemini drafter — if key + quota permit; otherwise it self-falls-back.
    if os.environ.get("GEMINI_API_KEY"):
        print()
        try:
            gemini = GeminiHinglishDrafter()
            gemini_events = _run_with_drafter(
                gemini, picks, Path("artifacts/promises_gemini.jsonl")
            )
            _print("GEMINI DRAFTER  (LLM-generated, tone-varied)", gemini_events)
        except Exception as e:  # noqa: BLE001
            print(f"Gemini drafter init failed: {e}")
    else:
        print("\n(GEMINI_API_KEY not set — skipping Gemini demo)")


if __name__ == "__main__":
    main()
