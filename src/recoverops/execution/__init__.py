"""Execution plane — the only place money actually moves."""

from .base import Executor
from .factory import get_executor
from .mock import MockExecutor, default_success_rates

__all__ = ["Executor", "MockExecutor", "default_success_rates", "get_executor"]
