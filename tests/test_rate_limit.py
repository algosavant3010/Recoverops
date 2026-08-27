"""Tests for the Gemini rate limiter and 429-aware backoff."""
from __future__ import annotations

import time

from recoverops.reasoning.gemini import GeminiDiagnoser, _RateLimiter


def test_rate_limiter_spaces_calls() -> None:
    limiter = _RateLimiter(requests_per_minute=120)  # min interval 0.5s
    limiter.wait()
    t0 = time.monotonic()
    limiter.wait()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.45, f"expected ~0.5s spacing, got {elapsed:.3f}s"


def test_rate_limiter_first_call_not_delayed() -> None:
    limiter = _RateLimiter(requests_per_minute=1)
    t0 = time.monotonic()
    limiter.wait()
    elapsed = time.monotonic() - t0
    assert elapsed < 0.1, "first wait must not sleep"


def test_backoff_honours_server_retry_delay() -> None:
    err = RuntimeError(
        "429 RESOURCE_EXHAUSTED. {'error': {..., "
        "'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', "
        "'retryDelay': '6.179539741s'}]}}"
    )
    wait = GeminiDiagnoser._compute_backoff(err, attempt=1)
    assert 6.5 <= wait <= 7.5, f"expected ~6.68s from parsed retryDelay, got {wait}"


def test_backoff_uses_exponential_when_no_hint() -> None:
    err = RuntimeError("some other transient error")
    w1 = GeminiDiagnoser._compute_backoff(err, attempt=1)
    w2 = GeminiDiagnoser._compute_backoff(err, attempt=2)
    w3 = GeminiDiagnoser._compute_backoff(err, attempt=3)
    assert w1 == 2.0
    assert w2 == 4.0
    assert w3 == 8.0


def test_backoff_caps_at_30_seconds() -> None:
    err = RuntimeError("some other transient error")
    assert GeminiDiagnoser._compute_backoff(err, attempt=10) == 30.0
