"""Typed domain models — the contracts between planes.

Money is carried in paise (int) throughout the system. Never use float for
money. Anything that touches a rupee amount uses `amount_paise: int`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .taxonomy import ActionKind, RecordType, RootCause


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False, use_enum_values=False)


# --------------------------------------------------------------------------- #
# Ingest
# --------------------------------------------------------------------------- #
class AtRiskRecord(_Base):
    """A single at-risk transaction. This is what the merchant hands us."""

    record_id: str
    record_type: RecordType
    merchant_id: str
    customer_id: str
    amount_paise: int = Field(ge=0)
    currency: str = "INR"
    error_code: str | None = None
    created_at: datetime
    last_attempt_at: datetime | None = None
    attempts: int = Field(default=0, ge=0)
    risk_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Ground truth — populated only by the synthetic generator, used only by
    # the evaluation harness. The agent must never read these fields.
    true_root_cause: RootCause | None = None
    true_recover_prob: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return v.upper()


# --------------------------------------------------------------------------- #
# Reason
# --------------------------------------------------------------------------- #
class Diagnosis(_Base):
    """Reasoning-plane output. Structured, so the policy plane can trust it."""

    record_id: str
    root_cause: RootCause
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    signals_used: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Decide
# --------------------------------------------------------------------------- #
class InterventionPlan(_Base):
    """A proposal from the reasoning plane. Not yet gated by policy."""

    record_id: str
    action: ActionKind
    params: dict[str, Any] = Field(default_factory=dict)
    proposed_at: datetime
    rationale: str


class PolicyDecision(_Base):
    """The gate's verdict on a proposed plan. Deterministic."""

    record_id: str
    plan: InterventionPlan
    allowed: bool
    rule_fired: str
    idempotency_key: str
    reason: str


# --------------------------------------------------------------------------- #
# Execute
# --------------------------------------------------------------------------- #
class ActionResult(_Base):
    """Outcome of one attempted action. One record can have many of these."""

    record_id: str
    idempotency_key: str
    action: ActionKind
    attempt_no: int = Field(ge=1)
    status: str  # e.g. "success", "failure", "duplicate", "timeout"
    recovered_amount_paise: int = Field(default=0, ge=0)
    error: str | None = None
    executed_at: datetime
    latency_ms: int = Field(default=0, ge=0)


class PromiseToPay(_Base):
    """A commitment captured from a B2B customer via the Hinglish channel."""

    record_id: str
    promised_date: datetime
    channel: str  # "whatsapp" | "voice" | "sms"
    language: str  # "en" | "hi" | "hinglish"
    captured_at: datetime
    status: str = "open"  # "open" | "kept" | "broken" | "renegotiated"


# --------------------------------------------------------------------------- #
# Observability
# --------------------------------------------------------------------------- #
class AuditEvent(_Base):
    """One line in the replayable audit log. Everything the agent did, why."""

    trace_id: str
    record_id: str
    stage: str  # "detect" | "diagnose" | "decide" | "gate" | "execute" | "stop"
    ts: datetime
    payload: dict[str, Any]
    rule_fired: str | None = None
