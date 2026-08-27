"""Seeded synthetic batch generator.

Produces two disjoint splits — `dev` and `holdout` — of `AtRiskRecord`s.
The generator seeds every source of randomness (Faker, `random`, timestamps)
so re-running with the same seed produces byte-identical output. Judges
should be able to reproduce our numbers with one command.

Each record carries a hidden `true_root_cause` and `true_recover_prob` for
the evaluation harness — the agent must not read these fields.

Output format: JSON Lines. One record per line. Streams cleanly, greps
easily, and matches what real audit pipelines emit.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

from ..models import AtRiskRecord
from ..taxonomy import (
    CAUSES_BY_RECORD_TYPE,
    ERROR_CODES_BY_CAUSE,
    RecordType,
    RootCause,
)

# Fixed "now" so runs are reproducible. Advance deliberately for new batches.
_FIXED_NOW = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

# Mix across record types (must sum to 1.0).
_RECORD_TYPE_MIX: dict[RecordType, float] = {
    RecordType.FAILED_PAYMENT: 0.55,
    RecordType.ABANDONED_CHECKOUT: 0.25,
    RecordType.FAILED_SUBSCRIPTION: 0.12,
    RecordType.OVERDUE_INVOICE: 0.08,
}

# Conditional mix of root cause given record type. Each inner dict sums to 1.
_CAUSE_MIX: dict[RecordType, dict[RootCause, float]] = {
    RecordType.FAILED_PAYMENT: {
        RootCause.INSUFFICIENT_FUNDS: 0.40,
        RootCause.GATEWAY_DOWNTIME: 0.20,
        RootCause.EXPIRED_CARD: 0.20,
        RootCause.FRAUD_SUSPECTED: 0.10,
        RootCause.UNKNOWN: 0.10,
    },
    RecordType.ABANDONED_CHECKOUT: {RootCause.CHECKOUT_ABANDONED: 1.0},
    RecordType.OVERDUE_INVOICE: {RootCause.B2B_OVERDUE: 1.0},
    RecordType.FAILED_SUBSCRIPTION: {
        RootCause.MANDATE_LAPSED: 0.50,
        RootCause.INSUFFICIENT_FUNDS: 0.30,
        RootCause.EXPIRED_CARD: 0.20,
    },
}

# Baseline probability that a record is recoverable given its true cause,
# assuming the *right* intervention. The evaluation simulator uses these.
_BASE_RECOVER_PROB: dict[RootCause, float] = {
    RootCause.INSUFFICIENT_FUNDS: 0.50,
    RootCause.GATEWAY_DOWNTIME: 0.75,
    RootCause.EXPIRED_CARD: 0.35,
    RootCause.MANDATE_LAPSED: 0.55,
    RootCause.CHECKOUT_ABANDONED: 0.30,
    RootCause.B2B_OVERDUE: 0.60,
    RootCause.FRAUD_SUSPECTED: 0.00,
    RootCause.UNKNOWN: 0.10,
}


@dataclass(frozen=True)
class GeneratorConfig:
    """All knobs for a batch generation run."""

    seed: int
    size: int
    split_name: str  # "dev" or "holdout"


def _weighted_choice(rng: random.Random, weights: dict) -> object:
    keys = list(weights.keys())
    probs = list(weights.values())
    total = math.fsum(probs)
    if not math.isclose(total, 1.0, abs_tol=1e-6):
        raise ValueError(f"weights must sum to 1.0, got {total}")
    return rng.choices(keys, weights=probs, k=1)[0]


def _sample_amount_paise(rng: random.Random, record_type: RecordType) -> int:
    """Log-normal-ish amounts, in paise, tuned per record type."""
    if record_type is RecordType.OVERDUE_INVOICE:
        rupees = int(rng.lognormvariate(mu=10.5, sigma=0.8))  # ~₹36k median
        rupees = max(10_000, min(rupees, 5_00_000))
    elif record_type is RecordType.FAILED_SUBSCRIPTION:
        rupees = rng.choice([99, 149, 199, 299, 499, 799, 999])
    else:
        rupees = int(rng.lognormvariate(mu=7.0, sigma=0.9))  # ~₹1.1k median
        rupees = max(50, min(rupees, 50_000))
    return rupees * 100


def _sample_recover_prob(rng: random.Random, cause: RootCause) -> float:
    """Per-record recover probability = base ± small noise, clipped to [0,1]."""
    base = _BASE_RECOVER_PROB[cause]
    noise = rng.gauss(0.0, 0.07)
    return max(0.0, min(1.0, base + noise))


def _sample_timestamps(
    rng: random.Random, record_type: RecordType, attempts: int
) -> tuple[datetime, datetime | None]:
    """Return (created_at, last_attempt_at). Within the 30-day pre-now window."""
    minutes_ago_created = rng.randint(60, 30 * 24 * 60)
    created_at = _FIXED_NOW - timedelta(minutes=minutes_ago_created)
    if record_type is RecordType.ABANDONED_CHECKOUT or attempts == 0:
        return created_at, None
    minutes_since_created = rng.randint(1, max(2, minutes_ago_created - 1))
    last_attempt_at = created_at + timedelta(minutes=minutes_since_created)
    return created_at, last_attempt_at


def _sample_error_code(rng: random.Random, cause: RootCause) -> str | None:
    codes = ERROR_CODES_BY_CAUSE.get(cause, ())
    if not codes:
        return None
    return rng.choice(codes)


def _sample_risk_flags(rng: random.Random, cause: RootCause) -> list[str]:
    if cause is RootCause.FRAUD_SUSPECTED:
        return rng.sample(
            ["velocity_spike", "bin_mismatch", "geo_anomaly", "device_reuse"],
            k=rng.randint(1, 2),
        )
    if rng.random() < 0.05:
        return ["low_signal_flag"]
    return []


def _sample_attempts(rng: random.Random, record_type: RecordType) -> int:
    if record_type is RecordType.ABANDONED_CHECKOUT:
        return 0
    return rng.choices([0, 1, 2, 3], weights=[0.1, 0.55, 0.25, 0.10], k=1)[0]


def _record_id(split: str, i: int) -> str:
    return f"rec_{split}_{i:06d}"


def _sanity_check_cause_for_type(record_type: RecordType, cause: RootCause) -> None:
    if cause not in CAUSES_BY_RECORD_TYPE[record_type]:
        raise AssertionError(f"cause {cause} not valid for record_type {record_type}")


def generate_batch(cfg: GeneratorConfig) -> Iterator[AtRiskRecord]:
    """Yield `cfg.size` reproducible `AtRiskRecord`s for the given split."""
    rng = random.Random(cfg.seed)
    faker = Faker("en_IN")
    Faker.seed(cfg.seed)

    for i in range(cfg.size):
        record_type: RecordType = _weighted_choice(rng, _RECORD_TYPE_MIX)  # type: ignore[assignment]
        cause: RootCause = _weighted_choice(rng, _CAUSE_MIX[record_type])  # type: ignore[assignment]
        _sanity_check_cause_for_type(record_type, cause)

        attempts = _sample_attempts(rng, record_type)
        created_at, last_attempt_at = _sample_timestamps(rng, record_type, attempts)

        yield AtRiskRecord(
            record_id=_record_id(cfg.split_name, i),
            record_type=record_type,
            merchant_id=f"acc_{faker.bothify(text='????####').upper()}",
            customer_id=f"cust_{faker.bothify(text='##########')}",
            amount_paise=_sample_amount_paise(rng, record_type),
            currency="INR",
            error_code=_sample_error_code(rng, cause),
            created_at=created_at,
            last_attempt_at=last_attempt_at,
            attempts=attempts,
            risk_flags=_sample_risk_flags(rng, cause),
            metadata={
                "channel": rng.choice(["web", "android", "ios"]),
                "city": faker.city(),
            },
            true_root_cause=cause,
            true_recover_prob=_sample_recover_prob(rng, cause),
        )


def write_jsonl(records: Iterable[AtRiskRecord], path: Path) -> int:
    """Write records to `path` as JSON Lines. Returns count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.model_dump_json())
            f.write("\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[AtRiskRecord]:
    """Stream `AtRiskRecord`s back from a JSONL file."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield AtRiskRecord.model_validate_json(line)


def generate_dev_and_holdout(
    out_dir: Path, dev_size: int, holdout_size: int, base_seed: int
) -> dict[str, Path]:
    """Generate both splits with disjoint seeds. Returns split_name -> path."""
    dev = GeneratorConfig(seed=base_seed, size=dev_size, split_name="dev")
    holdout = GeneratorConfig(seed=base_seed + 10_000, size=holdout_size, split_name="holdout")
    paths: dict[str, Path] = {}
    for cfg in (dev, holdout):
        path = out_dir / cfg.split_name / "batch.jsonl"
        write_jsonl(generate_batch(cfg), path)
        paths[cfg.split_name] = path
    return paths


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recoverops-gen-data",
        description="Generate reproducible synthetic at-risk batches (dev + holdout).",
    )
    parser.add_argument("--out", type=Path, default=Path("data"), help="output root dir")
    parser.add_argument("--dev-size", type=int, default=200)
    parser.add_argument("--holdout-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    paths = generate_dev_and_holdout(
        out_dir=args.out,
        dev_size=args.dev_size,
        holdout_size=args.holdout_size,
        base_seed=args.seed,
    )
    summary = {name: str(p) for name, p in paths.items()}
    print(json.dumps({"generated": summary, "seed": args.seed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
