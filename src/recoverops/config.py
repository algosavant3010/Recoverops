"""Guardrails configuration loader.

The YAML file at `config/guardrails.yaml` is the single source of truth for
every policy limit. This module loads and validates it into typed models so
the rest of the codebase never touches raw dicts.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .taxonomy import ActionKind, RootCause


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Caps(_StrictModel):
    max_retries_per_record: int = Field(ge=0)
    max_nudges_per_record: int = Field(ge=0)
    max_total_actions_per_record: int = Field(ge=0)
    max_discount_pct: float = Field(ge=0, le=100)
    max_actions_per_batch: int = Field(ge=0)


class Cooldowns(_StrictModel):
    retry_hours: int = Field(ge=0)
    nudge_hours: int = Field(ge=0)
    outreach_hours: int = Field(ge=0)


class StoppingRules(_StrictModel):
    stop_on_success: bool
    stop_on_fraud_flag: bool
    stop_on_customer_optout: bool
    max_wallclock_days: int = Field(ge=1)


class QuietHours(_StrictModel):
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=0, le=23)


class OutreachPolicy(_StrictModel):
    supported_languages: list[str]
    quiet_hours_local: QuietHours
    max_messages_per_day: int = Field(ge=0)


class Idempotency(_StrictModel):
    key_ttl_hours: int = Field(ge=1)


class InterventionPolicy(_StrictModel):
    actions: list[ActionKind]
    retry_strategy: str | None = None
    incentive_max_pct: float | None = Field(default=None, ge=0, le=100)


class Guardrails(_StrictModel):
    version: int
    seed: int
    caps: Caps
    cooldowns: Cooldowns
    stopping_rules: StoppingRules
    outreach: OutreachPolicy
    idempotency: Idempotency
    interventions: dict[RootCause, InterventionPolicy]

    def allowed_actions(self, cause: RootCause) -> list[ActionKind]:
        """Return the closed set of actions allowed for a diagnosed cause."""
        return list(self.interventions[cause].actions)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "guardrails.yaml"


def load_guardrails(path: Path | str | None = None) -> Guardrails:
    """Load and validate the guardrails file. Raises on any schema drift."""
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Guardrails.model_validate(raw)
