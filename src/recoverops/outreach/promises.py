"""Promise-to-pay store — append-only JSONL, cheap to query."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

from ..models import PromiseToPay


class PromiseToPayStore:
    """Append-only, one JSON object per line. Load-on-read."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()

    @property
    def path(self) -> Path:
        return self._path

    def append(self, promise: PromiseToPay) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(promise.model_dump_json())
            f.write("\n")

    def all(self) -> list[PromiseToPay]:
        return list(self._read())

    def by_status(self, status: str) -> list[PromiseToPay]:
        return [p for p in self._read() if p.status == status]

    def count(self) -> int:
        return sum(1 for _ in self._read())

    def _read(self) -> Iterator[PromiseToPay]:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield PromiseToPay.model_validate_json(line)

    def clear(self) -> None:
        """Truncate the file. Use in tests and demos only."""
        self._path.write_text("", encoding="utf-8")

    def latest_before(self, cutoff: datetime) -> list[PromiseToPay]:
        return [p for p in self._read() if p.captured_at <= cutoff]
