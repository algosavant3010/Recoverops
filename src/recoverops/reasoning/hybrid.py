"""Hybrid diagnoser: Gemini primary, rule-based fallback.

Trigger conditions for the fallback:
  1. Primary raises (rate limit, network, quota, safety filter, etc.).
  2. Primary returns a diagnosis below the configured confidence floor.

Why: at demo time we can't afford a batch that dies halfway because the free
tier ran out. Judges won't get to see the recovered money if a 429 kills the
run. This class is the seatbelt.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..models import Diagnosis
from .base import Diagnoser
from .signals import RecordSignals

logger = logging.getLogger(__name__)


@dataclass
class HybridStats:
    primary_used: int = 0
    fallback_low_conf: int = 0
    fallback_error: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.primary_used + self.fallback_low_conf + self.fallback_error


class HybridDiagnoser:
    """Composes a primary and a fallback diagnoser under one interface."""

    name = "hybrid_v1"

    def __init__(
        self,
        primary: Diagnoser,
        fallback: Diagnoser,
        min_confidence: float = 0.5,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._min_confidence = min_confidence
        self.stats = HybridStats()

    def diagnose(self, signals: RecordSignals) -> Diagnosis:
        try:
            d = self._primary.diagnose(signals)
        except Exception as e:
            logger.warning("primary diagnoser failed (%s); falling back to %s", e, self._fallback.name)
            self.stats.fallback_error += 1
            self.stats.errors.append(str(e)[:200])
            return self._tagged(self._fallback.diagnose(signals), reason="error")

        if d.confidence >= self._min_confidence:
            self.stats.primary_used += 1
            return d

        self.stats.fallback_low_conf += 1
        return self._tagged(self._fallback.diagnose(signals), reason="low_conf")

    @staticmethod
    def _tagged(d: Diagnosis, *, reason: str) -> Diagnosis:
        return d.model_copy(update={"reasoning": f"[fallback:{reason}] {d.reasoning}"})
