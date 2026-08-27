"""Hinglish outreach drafters.

Two implementations:
  * `GeminiHinglishDrafter` — LLM-drafted, culturally appropriate, tone-varied.
  * `TemplateHinglishDrafter` — zero-cost fallback with a fixed structure.

Both return the same `DraftedMessage` contract so the agent doesn't care
which one is active. `GeminiHinglishDrafter` transparently falls back to
the template on any error (quota, network, safety filter, parse failure)
so the demo never dies.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-3.6-flash"
_DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "hinglish_p2p_v1.md"


@dataclass(frozen=True)
class OutreachContext:
    """The redacted view the drafter sees. No PII, no ground-truth."""

    record_id: str
    amount_paise: int
    currency: str
    days_overdue: int


class DraftedMessage(BaseModel):
    """The drafter's structured output."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=20, max_length=400)
    suggested_promise_days: int = Field(ge=1, le=14)
    tone: str
    channel: str = "whatsapp"
    language: str = "hinglish"


class _GeminiDraftOut(BaseModel):
    """Wire schema from the model."""

    message: str
    suggested_promise_days: int = Field(ge=1, le=14)
    tone: str = "polite_reminder"


@runtime_checkable
class HinglishDrafter(Protocol):
    name: str

    def draft(self, ctx: OutreachContext) -> DraftedMessage:
        ...


class TemplateHinglishDrafter:
    """Deterministic template. Always works, needs no network."""

    name = "template_v1"

    def draft(self, ctx: OutreachContext) -> DraftedMessage:
        amount_rupees = ctx.amount_paise // 100
        days = 5 if ctx.amount_paise <= 50_000_00 else 3
        msg = (
            f"Namaste ji, aapka invoice {ctx.record_id} ka amount "
            f"Rs. {amount_rupees:,} pending hai ({ctx.days_overdue} din se). "
            f"Kya aap next {days} working days mein settle kar sakte hain? "
            f"Thoda confirm kar dijiye. — Team RecoverOps"
        )
        return DraftedMessage(
            message=msg,
            suggested_promise_days=days,
            tone="polite_reminder",
        )


class GeminiHinglishDrafter:
    """LLM drafter with automatic template fallback on any error."""

    name = "gemini_hinglish_v1"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        prompt_path: Path | None = None,
        fallback: HinglishDrafter | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self._model_name = model_name or os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
        self._prompt = (prompt_path or _DEFAULT_PROMPT_PATH).read_text(encoding="utf-8")
        self._fallback = fallback or TemplateHinglishDrafter()
        self._client = self._init_client()

    def _init_client(self) -> Any:
        from google import genai
        from google.genai import types

        raw = genai.Client(api_key=self._api_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_GeminiDraftOut,
            temperature=0.6,   # room for tone variation
        )
        # Reuse the reasoning-plane adapter shape for consistency.
        from ..reasoning.gemini import _GenaiAdapter

        return _GenaiAdapter(client=raw, model_name=self._model_name, generation_config=config)

    def draft(self, ctx: OutreachContext) -> DraftedMessage:
        prompt = self._render(ctx)
        try:
            response = self._client.generate_content(prompt)
            text = getattr(response, "text", None) or ""
            parsed = _GeminiDraftOut.model_validate_json(text)
            return DraftedMessage(
                message=parsed.message.strip(),
                suggested_promise_days=parsed.suggested_promise_days,
                tone=parsed.tone,
            )
        except (ValidationError, Exception) as e:  # noqa: BLE001 — we WANT broad catch
            logger.warning("hinglish gemini draft failed (%s); using template", _short(e))
            return self._fallback.draft(ctx)

    def _render(self, ctx: OutreachContext) -> str:
        payload = {
            "invoice_id": ctx.record_id,
            "amount_paise": ctx.amount_paise,
            "currency": ctx.currency,
            "days_overdue": ctx.days_overdue,
        }
        return self._prompt.replace("{context_json}", json.dumps(payload, indent=2))


def _short(e: Exception) -> str:
    s = str(e)
    return s if len(s) <= 120 else s[:117] + "..."


def get_hinglish_drafter(kind: str | None = None) -> HinglishDrafter:
    """Env-driven pick. `auto` = Gemini if key present, else template."""
    kind = (kind or os.environ.get("RECOVEROPS_HINGLISH") or "auto").lower()
    if kind == "template":
        return TemplateHinglishDrafter()
    if kind == "gemini":
        return GeminiHinglishDrafter()
    if kind == "auto":
        if not os.environ.get("GEMINI_API_KEY"):
            return TemplateHinglishDrafter()
        try:
            return GeminiHinglishDrafter()
        except Exception as e:  # noqa: BLE001
            logger.warning("gemini hinglish drafter init failed (%s); using template", _short(e))
            return TemplateHinglishDrafter()
    raise ValueError(f"unknown hinglish drafter kind: {kind!r}")
