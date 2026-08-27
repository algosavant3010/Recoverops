"""Executor factory.

`RECOVEROPS_EXECUTOR` selects: `mock` (default) or `razorpay`.
The Razorpay adapter is a real test-mode integration and is scheduled for
Phase 9 polish; the mock exposes the same interface so the agent loop is
executor-agnostic today.
"""
from __future__ import annotations

import os

from ..policy.store import IdempotencyStore
from .base import Executor
from .mock import MockExecutor


def get_executor(
    kind: str | None = None,
    *,
    store: IdempotencyStore,
    seed: int = 0,
) -> Executor:
    kind = (kind or os.environ.get("RECOVEROPS_EXECUTOR") or "mock").lower()

    if kind == "mock":
        return MockExecutor(store=store, seed=seed)

    if kind == "razorpay":
        raise NotImplementedError(
            "Razorpay test-mode executor is Phase-9 polish. "
            "The Executor protocol is stable; drop-in without touching the agent."
        )

    raise ValueError(f"unknown executor kind: {kind!r}")
