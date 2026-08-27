"""CLI: run the evaluation and print the report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from recoverops.data.generator import read_jsonl
from recoverops.eval import evaluate_all, write_report


def _inr(paise: int) -> str:
    return f"Rs. {paise/100:>12,.2f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recoverops-eval")
    parser.add_argument(
        "--batch",
        type=Path,
        default=Path("data/holdout/batch.jsonl"),
        help="Path to a JSONL batch (default: data/holdout/batch.jsonl)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts"),
        help="Directory for eval_report.json + eval_report.md",
    )
    args = parser.parse_args(argv)

    records = list(read_jsonl(args.batch))
    if not records:
        print(f"no records in {args.batch}", file=sys.stderr)
        return 2

    report = evaluate_all(records)
    paths = write_report(report, args.out)

    print("=" * 78)
    print(f"RECOVEROPS EVALUATION  ·  batch={args.batch}  ({len(records)} records)")
    print("=" * 78)
    print()
    print(f"{'Strategy':<20s} {'Records':>10s} {'Amount recovered':>22s} {'Rate':>8s}")
    print("-" * 78)
    for s in report.strategies:
        print(
            f"{s.name:<20s} {s.records_recovered:>4d}/{s.records_processed:<5d}"
            f" {_inr(s.total_recovered_paise):>22s} {s.recovery_rate:>7.1%}"
        )
    print()
    print(f"Lift over naive_retry_3x:  {report.lift_over_naive_pp:+.2f} pp")
    print(f"Lift over no_op:           {report.lift_over_no_op_pp:+.2f} pp")
    print()
    print(f"Diagnosis accuracy:        {report.diagnosis_accuracy:.2%}")
    print()
    print("Top exceptions (unrecovered):")
    buckets: dict[str, tuple[int, int]] = {}
    for e in report.exceptions:
        cnt, amt = buckets.get(e.reason, (0, 0))
        buckets[e.reason] = (cnt + 1, amt + e.amount_paise)
    for reason, (cnt, amt) in sorted(buckets.items(), key=lambda x: -x[1][0]):
        print(f"  {reason:<40s} {cnt:>4d}  {_inr(amt):>18s}")
    print()
    print(f"Report written to:")
    print(f"  {paths['json']}")
    print(f"  {paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
