"""Observable signals passed to the diagnoser.

`RecordSignals` is the *only* thing the reasoning plane sees. It is derived
from an `AtRiskRecord` by `signals_from_record`, which deliberately drops
ground-truth fields (`true_root_cause`, `true_recover_prob`) and PII
(`customer_id`). If a field isn't on this model, the LLM cannot cheat.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models import AtRiskRecord
from ..taxonomy import RecordType


class RecordSignals(BaseModel):
    """The redacted view of an at-risk record. What the diagnoser sees."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    record_type: RecordType
    amount_paise: int = Field(ge=0)
    currency: str
    error_code: str | None
    attempts: int = Field(ge=0)
    risk_flags: list[str]
    hours_since_created: float = Field(ge=0)
    hours_since_last_attempt: float | None
    has_prior_attempt: bool
    safe_metadata: dict[str, Any]


_SAFE_METADATA_KEYS = frozenset({"channel", "city"})


def signals_from_record(record: AtRiskRecord, now: datetime | None = None) -> RecordSignals:
    """Redact an `AtRiskRecord` down to observable signals only.

    Ground-truth fields and PII are stripped. This function is the single
    trust boundary between the ingest layer and the reasoning plane.
    """
    ref = now or datetime.now(timezone.utc)
    hours_since_created = max(0.0, (ref - record.created_at).total_seconds() / 3600)
    if record.last_attempt_at is not None:
        hours_since_last_attempt: float | None = max(
            0.0, (ref - record.last_attempt_at).total_seconds() / 3600
        )
    else:
        hours_since_last_attempt = None
    safe_metadata = {k: v for k, v in record.metadata.items() if k in _SAFE_METADATA_KEYS}
    return RecordSignals(
        record_id=record.record_id,
        record_type=record.record_type,
        amount_paise=record.amount_paise,
        currency=record.currency,
        error_code=record.error_code,
        attempts=record.attempts,
        risk_flags=list(record.risk_flags),
        hours_since_created=hours_since_created,
        hours_since_last_attempt=hours_since_last_attempt,
        has_prior_attempt=record.last_attempt_at is not None,
        safe_metadata=safe_metadata,
    )
