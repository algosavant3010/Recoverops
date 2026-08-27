"""Replay tool — reconstruct a `RunReport` from an audit log alone.

If the numbers we quote in the pitch video can be reproduced by piping the
log into this script, the audit log is provably complete. That's the whole
point of shipping it.

Usage:
    python -m recoverops.observability.replay --log logs/run_....jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ..agent.loop import RunReport
from .audit import read_events


def replay_report(path: Path | str) -> RunReport:
    """Reconstruct the batch report from the events in `path`."""
    report = RunReport()
    seen_ingest: set[str] = set()
    blocks: Counter[str] = Counter()
    terminals: Counter[str] = Counter()

    for event in read_events(path):
        stage = event.get("stage")
        payload = event.get("payload", {})

        if stage == "ingest":
            record_id = event.get("record_id")
            if record_id in seen_ingest:
                continue
            seen_ingest.add(record_id)
            report.records_processed += 1
            report.total_at_risk_paise += int(payload.get("amount_paise", 0))

        elif stage == "gate":
            decision = payload.get("decision", {})
            if decision.get("allowed") is False:
                report.actions_blocked += 1
                rule = decision.get("rule_fired") or "unknown"
                blocks[rule] += 1

        elif stage == "execute":
            result = payload.get("result", {})
            status = result.get("status")
            if status == "duplicate":
                report.duplicates_prevented += 1
            else:
                report.actions_attempted += 1
                if status == "success":
                    report.total_recovered_paise += int(
                        result.get("recovered_amount_paise", 0)
                    )

        elif stage == "terminal":
            reason = payload.get("reason") or "unknown"
            terminals[reason] += 1

    report.blocks_by_rule = dict(blocks)
    report.terminal_by_reason = dict(terminals)
    return report


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recoverops-replay",
        description="Reconstruct a batch report from an audit log.",
    )
    parser.add_argument("--log", type=Path, required=True, help="path to a JSONL audit log")
    args = parser.parse_args(argv)

    report = replay_report(args.log)
    output = {
        "records_processed": report.records_processed,
        "total_at_risk_paise": report.total_at_risk_paise,
        "total_recovered_paise": report.total_recovered_paise,
        "recovery_rate": round(report.recovery_rate, 4),
        "actions_attempted": report.actions_attempted,
        "actions_blocked": report.actions_blocked,
        "duplicates_prevented": report.duplicates_prevented,
        "blocks_by_rule": report.blocks_by_rule,
        "terminal_by_reason": report.terminal_by_reason,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
