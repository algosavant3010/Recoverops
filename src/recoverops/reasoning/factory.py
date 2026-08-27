"""Diagnoser factory — env-driven selection with a safe fallback.

`RECOVEROPS_DIAGNOSER` controls the pick:
    auto (default) — Hybrid (Gemini primary + rules fallback) if key present, else rules
    hybrid         — force Hybrid (raises if key missing)
    gemini         — force Gemini alone (raises if key missing)
    rules          — force rule-based fallback
"""
from __future__ import annotations

import logging
import os

from .base import Diagnoser
from .rules import RuleBasedDiagnoser

logger = logging.getLogger(__name__)


def get_diagnoser(kind: str | None = None) -> Diagnoser:
    """Return a `Diagnoser` per the requested (or env-selected) kind."""
    kind = (kind or os.environ.get("RECOVEROPS_DIAGNOSER") or "auto").lower()

    if kind == "rules":
        return RuleBasedDiagnoser()

    if kind == "gemini":
        from .gemini import GeminiDiagnoser  # imported lazily so `rules` needs no SDK
        return GeminiDiagnoser()

    if kind == "hybrid":
        from .gemini import GeminiDiagnoser
        from .hybrid import HybridDiagnoser
        return HybridDiagnoser(primary=GeminiDiagnoser(), fallback=RuleBasedDiagnoser())

    if kind == "auto":
        if not os.environ.get("GEMINI_API_KEY"):
            logger.info("no GEMINI_API_KEY set; using rule-based diagnoser")
            return RuleBasedDiagnoser()
        try:
            from .gemini import GeminiDiagnoser
            from .hybrid import HybridDiagnoser
            return HybridDiagnoser(primary=GeminiDiagnoser(), fallback=RuleBasedDiagnoser())
        except Exception as e:
            logger.warning("hybrid init failed (%s); falling back to rules", e)
            return RuleBasedDiagnoser()

    raise ValueError(f"unknown diagnoser kind: {kind!r}")
