"""Idempotency store — the single source of truth for whether an action
with a given key has already been reserved or executed.

`check_and_reserve` is the *atomic* operation the executor uses. If it
returns False, the caller must not execute; the action was already claimed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


class IdempotencyStore:
    """In-process TTL store. Swap for Redis in production; the API is stable."""

    def __init__(self, ttl_hours: int, now_fn: Callable[[], datetime] | None = None) -> None:
        self._ttl = timedelta(hours=ttl_hours)
        self._now = now_fn or _default_now
        self._store: dict[str, datetime] = {}

    def check_and_reserve(self, key: str) -> bool:
        """Reserve `key` atomically. Returns True if newly reserved, False if
        a live reservation already exists — in which case the caller MUST
        NOT execute the action."""
        self._gc()
        if key in self._store:
            return False
        self._store[key] = self._now()
        return True

    def contains(self, key: str) -> bool:
        self._gc()
        return key in self._store

    def size(self) -> int:
        self._gc()
        return len(self._store)

    def _gc(self) -> None:
        cutoff = self._now() - self._ttl
        expired = [k for k, ts in self._store.items() if ts < cutoff]
        for k in expired:
            del self._store[k]
