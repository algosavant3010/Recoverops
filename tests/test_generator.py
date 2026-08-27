"""Reproducibility + realism tests for the synthetic generator."""
from __future__ import annotations

import json
from pathlib import Path

from recoverops.data.generator import (
    GeneratorConfig,
    generate_batch,
    generate_dev_and_holdout,
    read_jsonl,
    write_jsonl,
)
from recoverops.taxonomy import CAUSES_BY_RECORD_TYPE, RecordType, RootCause


def test_generation_is_deterministic() -> None:
    cfg = GeneratorConfig(seed=123, size=50, split_name="dev")
    a = [r.model_dump_json() for r in generate_batch(cfg)]
    b = [r.model_dump_json() for r in generate_batch(cfg)]
    assert a == b, "same seed must produce byte-identical output"


def test_different_seeds_diverge() -> None:
    a = list(generate_batch(GeneratorConfig(seed=1, size=20, split_name="dev")))
    b = list(generate_batch(GeneratorConfig(seed=2, size=20, split_name="dev")))
    assert [r.record_id for r in a] == [r.record_id for r in b]
    assert any(x.model_dump() != y.model_dump() for x, y in zip(a, b))


def test_ground_truth_cause_is_valid_for_record_type() -> None:
    for rec in generate_batch(GeneratorConfig(seed=7, size=200, split_name="dev")):
        assert rec.true_root_cause is not None
        assert rec.true_root_cause in CAUSES_BY_RECORD_TYPE[rec.record_type]


def test_abandoned_checkouts_have_zero_attempts_and_no_error() -> None:
    for rec in generate_batch(GeneratorConfig(seed=7, size=200, split_name="dev")):
        if rec.record_type is RecordType.ABANDONED_CHECKOUT:
            assert rec.attempts == 0
            assert rec.error_code is None
            assert rec.last_attempt_at is None


def test_amounts_are_positive_integers_in_paise() -> None:
    for rec in generate_batch(GeneratorConfig(seed=7, size=200, split_name="dev")):
        assert isinstance(rec.amount_paise, int)
        assert rec.amount_paise > 0


def test_fraud_records_carry_risk_flags() -> None:
    fraud = [
        r
        for r in generate_batch(GeneratorConfig(seed=7, size=500, split_name="dev"))
        if r.true_root_cause is RootCause.FRAUD_SUSPECTED
    ]
    assert fraud, "expected some fraud_suspected records at n=500"
    assert all(r.risk_flags for r in fraud)


def test_dev_and_holdout_have_disjoint_ids(tmp_path: Path) -> None:
    paths = generate_dev_and_holdout(tmp_path, dev_size=40, holdout_size=40, base_seed=99)
    dev_ids = {r.record_id for r in read_jsonl(paths["dev"])}
    holdout_ids = {r.record_id for r in read_jsonl(paths["holdout"])}
    assert dev_ids.isdisjoint(holdout_ids)
    assert len(dev_ids) == 40 and len(holdout_ids) == 40


def test_jsonl_roundtrip(tmp_path: Path) -> None:
    cfg = GeneratorConfig(seed=5, size=25, split_name="dev")
    path = tmp_path / "dev" / "batch.jsonl"
    n = write_jsonl(generate_batch(cfg), path)
    assert n == 25
    reloaded = list(read_jsonl(path))
    assert len(reloaded) == 25
    # File must be strict JSONL — one valid JSON object per line, no trailing junk.
    for line in path.read_text(encoding="utf-8").splitlines():
        json.loads(line)


def test_ground_truth_recover_probs_in_unit_interval() -> None:
    for rec in generate_batch(GeneratorConfig(seed=11, size=100, split_name="dev")):
        assert rec.true_recover_prob is not None
        assert 0.0 <= rec.true_recover_prob <= 1.0
