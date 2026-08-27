"""Structured audit log — one JSON line per event, one trace-id per record.

Design contract:
  * Every event carries a `trace_id` derived deterministically from
    `(run_id, record_id)` — the same batch replayed reproduces the same
    trace ids, so the log is stable and grep-friendly.
  * Every event carries `run_id`, `stage`, `ts`, and the raw `payload`
    the agent chose to emit. If a payload contains a policy decision, the
    top-level `rule_fired` is promoted for cheap filtering (`jq
    '.rule_fired'`).
  * Writes are line-buffered with immediate flush so a mid-batch crash
    still leaves a truthful (partial) log.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TextIO


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_run_id(now: datetime) -> str:
    return "run_" + now.strftime("%Y%m%dT%H%M%SZ")


def _make_trace_id(run_id: str, record_id: str) -> str:
    digest = hashlib.sha256(f"{run_id}|{record_id}".encode("utf-8")).hexdigest()[:16]
    return f"trace_{digest}"


class AuditLog:
    """Line-oriented JSON audit log. Use as an `on_event` callback."""

    def __init__(
        self,
        path: Path | str,
        *,
        run_id: str | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._now = now_fn or _default_now
        self._run_id = run_id or _default_run_id(self._now())
        self._f: TextIO = self._path.open("a", encoding="utf-8")
        self._traces: dict[str, str] = {}
        self._closed = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def run_id(self) -> str:
        return self._run_id

    def trace_id(self, record_id: str) -> str:
        if record_id not in self._traces:
            self._traces[record_id] = _make_trace_id(self._run_id, record_id)
        return self._traces[record_id]

    def emit(self, stage: str, payload: dict[str, Any]) -> None:
        """Write one event. Safe to pass directly as `on_event` to the agent."""
        if self._closed:
            raise RuntimeError("audit log already closed")
        record_id = payload.get("record_id")
        if not isinstance(record_id, str):
            raise ValueError(f"payload for stage {stage!r} missing record_id")

        event = {
            "run_id": self._run_id,
            "trace_id": self.trace_id(record_id),
            "record_id": record_id,
            "stage": stage,
            "ts": self._now().isoformat().replace("+00:00", "Z"),
            "rule_fired": _extract_rule(stage, payload),
            "payload": payload,
        }
        self._f.write(json.dumps(event, separators=(",", ":"), sort_keys=True))
        self._f.write("\n")
        self._f.flush()

    def __call__(self, stage: str, payload: dict[str, Any]) -> None:
        """Callable form so this class can be handed directly to `on_event`."""
        self.emit(stage, payload)

    def close(self) -> None:
        if not self._closed:
            self._f.close()
            self._closed = True

    def __enter__(self) -> AuditLog:
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN001
        self.close()


def _extract_rule(stage: str, payload: dict[str, Any]) -> str | None:
    """Promote policy `rule_fired` to a top-level column when it applies."""
    if stage != "gate":
        return None
    decision = payload.get("decision")
    if isinstance(decision, dict):
        rule = decision.get("rule_fired")
        return rule if isinstance(rule, str) else None
    return None


def read_events(path: Path | str) -> list[dict[str, Any]]:
    """Load an audit log back into memory. Cheap at demo scale."""
    events: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events
