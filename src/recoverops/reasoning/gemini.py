"""Gemini-backed diagnoser with strict structured output.

Design contract:
  * The LLM produces a JSON object matching `_GeminiOut` — nothing else.
  * We validate to a `Diagnosis` and clip the label into the closed set.
  * On parse failure or invalid label we retry once, then fall back to
    `RootCause.UNKNOWN` with confidence 0.0 — the policy engine will
    downstream-decide what to do with that (typically: escalate).
  * A small in-process cache keyed by the signals payload keeps free-tier
    rate limits comfortable during batch runs.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ..models import Diagnosis
from ..taxonomy import RootCause
from .signals import RecordSignals

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-3.6-flash"
_DEFAULT_RPM = 5   # Gemini free-tier default for flash models.
_DEFAULT_RETRIES = 4
_DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "diagnose_v1.md"

_RETRY_DELAY_RE = re.compile(r"'retryDelay':\s*'(\d+(?:\.\d+)?)s'")


class _RateLimiter:
    """Simple monotonic-clock spacer. Not thread-safe by design (single agent)."""

    def __init__(self, requests_per_minute: int) -> None:
        self._min_interval = 60.0 / max(1, requests_per_minute)
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()


class _GeminiOut(BaseModel):
    """Wire schema — validated before we trust anything from the model."""

    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    signals_used: list[str] = Field(default_factory=list)


class _GenaiAdapter:
    """Thin adapter so the rest of this module talks to one stable interface."""

    def __init__(self, client: Any, model_name: str, generation_config: dict[str, Any]) -> None:
        self._client = client
        self._model_name = model_name
        self._config = generation_config

    def generate_content(self, prompt: str) -> Any:
        return self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=self._config,
        )


class GeminiDiagnoser:
    """Google Gen AI diagnoser. Requires GEMINI_API_KEY in env."""

    name = "gemini_v1"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        prompt_path: Path | None = None,
        cache_size: int = 4096,
        requests_per_minute: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Put it in .env or the process environment."
            )
        self._model_name = model_name or os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
        self._prompt = (prompt_path or _DEFAULT_PROMPT_PATH).read_text(encoding="utf-8")
        self._cache: dict[str, Diagnosis] = {}
        self._cache_size = cache_size
        rpm = requests_per_minute or int(os.environ.get("GEMINI_RPM", _DEFAULT_RPM))
        self._limiter = _RateLimiter(rpm)
        self._max_retries = max_retries or int(os.environ.get("GEMINI_RETRIES", _DEFAULT_RETRIES))
        self._client = self._init_client()

    def _init_client(self) -> Any:
        from google import genai
        from google.genai import types

        raw = genai.Client(api_key=self._api_key)
        # response_schema pins the wire contract on the API side, not just ours.
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_GeminiOut,
            temperature=0.1,
        )
        return _GenaiAdapter(client=raw, model_name=self._model_name, generation_config=config)

    def diagnose(self, signals: RecordSignals) -> Diagnosis:
        key = self._cache_key(signals)
        cached = self._cache.get(key)
        if cached is not None:
            return cached.model_copy(update={"record_id": signals.record_id})

        prompt = self._render_prompt(signals)
        raw = self._call_with_retry(prompt, attempts=self._max_retries)
        diagnosis = self._parse(raw, signals)

        if len(self._cache) < self._cache_size:
            self._cache[key] = diagnosis
        return diagnosis

    def _render_prompt(self, signals: RecordSignals) -> str:
        payload = signals.model_dump(mode="json")
        payload.pop("record_id", None)  # ID is not a diagnostic signal
        return self._prompt.replace("{signals_json}", json.dumps(payload, indent=2))

    def _call_with_retry(self, prompt: str, *, attempts: int) -> str:
        last_err: Exception | None = None
        for i in range(1, attempts + 1):
            try:
                self._limiter.wait()
                response = self._client.generate_content(prompt)
                text = getattr(response, "text", None) or ""
                if text.strip():
                    return text
                last_err = RuntimeError("empty response from model")
            except Exception as e:  # network / quota / safety filter
                last_err = e

            if i < attempts:
                wait = self._compute_backoff(last_err, i)
                logger.warning(
                    "gemini attempt %d/%d failed (%s); backing off %.1fs",
                    i, attempts, _short_err(last_err), wait,
                )
                time.sleep(wait)
        raise RuntimeError(f"gemini failed after {attempts} attempts: {_short_err(last_err)}")

    @staticmethod
    def _compute_backoff(err: Exception | None, attempt: int) -> float:
        # Respect server-side retryDelay hints for 429s.
        if err is not None:
            m = _RETRY_DELAY_RE.search(str(err))
            if m:
                return float(m.group(1)) + 0.5
        # Exponential backoff otherwise: 1s, 2s, 4s, 8s, ...
        return min(2.0 ** attempt, 30.0)

    def _parse(self, raw: str, signals: RecordSignals) -> Diagnosis:
        try:
            parsed = _GeminiOut.model_validate_json(raw)
        except ValidationError as e:
            logger.warning("gemini output failed schema validation: %s", e)
            return self._fallback(signals, reason="schema_invalid")

        try:
            cause = RootCause(parsed.root_cause)
        except ValueError:
            logger.warning("gemini returned out-of-taxonomy label: %r", parsed.root_cause)
            return self._fallback(signals, reason="label_out_of_taxonomy")

        return Diagnosis(
            record_id=signals.record_id,
            root_cause=cause,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning[:500],
            signals_used=parsed.signals_used[:16],
        )

    def _fallback(self, signals: RecordSignals, *, reason: str) -> Diagnosis:
        return Diagnosis(
            record_id=signals.record_id,
            root_cause=RootCause.UNKNOWN,
            confidence=0.0,
            reasoning=f"gemini_fallback:{reason}",
            signals_used=[],
        )

    @staticmethod
    def _cache_key(signals: RecordSignals) -> str:
        payload = signals.model_dump(mode="json")
        payload.pop("record_id", None)
        return json.dumps(payload, sort_keys=True)


def _short_err(e: Exception | None) -> str:
    if e is None:
        return "unknown"
    s = str(e)
    return s if len(s) <= 160 else s[:157] + "..."
