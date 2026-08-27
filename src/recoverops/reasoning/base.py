"""Diagnoser protocol — every implementation returns a `Diagnosis`."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import Diagnosis
from .signals import RecordSignals


@runtime_checkable
class Diagnoser(Protocol):
    """A stateless function-object that classifies signals into a root cause."""

    name: str

    def diagnose(self, signals: RecordSignals) -> Diagnosis:
        """Return a `Diagnosis`. Must never raise on well-formed signals."""
        ...
