"""Hinglish drafter + promise store tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from recoverops.models import PromiseToPay
from recoverops.outreach.hinglish import (
    DraftedMessage,
    GeminiHinglishDrafter,
    OutreachContext,
    TemplateHinglishDrafter,
    get_hinglish_drafter,
)
from recoverops.outreach.promises import PromiseToPayStore


def _ctx() -> OutreachContext:
    return OutreachContext(
        record_id="INV-1029",
        amount_paise=12_000_00,
        currency="INR",
        days_overdue=7,
    )


def test_template_drafter_is_deterministic() -> None:
    d = TemplateHinglishDrafter()
    a = d.draft(_ctx())
    b = d.draft(_ctx())
    assert a.message == b.message
    assert a.suggested_promise_days == b.suggested_promise_days


def test_template_message_contains_record_and_amount() -> None:
    m = TemplateHinglishDrafter().draft(_ctx()).message
    assert "INV-1029" in m
    assert "12,000" in m
    assert "Team RecoverOps" in m


def test_template_uses_hinglish_markers() -> None:
    m = TemplateHinglishDrafter().draft(_ctx()).message
    lowered = m.lower()
    assert any(k in lowered for k in ("namaste", "namaskar", "hi ji"))
    assert any(k in lowered for k in ("aap", "kya", "kar")), "no Hindi cue words"


def test_template_length_within_bounds() -> None:
    m = TemplateHinglishDrafter().draft(_ctx()).message
    assert 60 <= len(m) <= 400


def test_template_forbids_devanagari() -> None:
    m = TemplateHinglishDrafter().draft(_ctx()).message
    # Devanagari block: U+0900..U+097F.
    assert not any("\u0900" <= ch <= "\u097F" for ch in m)


def test_promise_store_roundtrip(tmp_path: Path) -> None:
    store = PromiseToPayStore(tmp_path / "promises.jsonl")
    now = datetime(2026, 8, 28, tzinfo=timezone.utc)
    p1 = PromiseToPay(
        record_id="INV-1",
        promised_date=now,
        channel="whatsapp",
        language="hinglish",
        captured_at=now,
    )
    p2 = p1.model_copy(update={"record_id": "INV-2", "status": "kept"})
    store.append(p1)
    store.append(p2)

    all_ = store.all()
    assert [p.record_id for p in all_] == ["INV-1", "INV-2"]
    assert store.count() == 2
    assert [p.record_id for p in store.by_status("open")] == ["INV-1"]
    assert [p.record_id for p in store.by_status("kept")] == ["INV-2"]


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload if isinstance(payload, str) else json.dumps(payload)
        self.calls = 0

    def generate_content(self, prompt: str) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(text=self._payload)


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test")


def _build_gemini(monkeypatch, client):
    monkeypatch.setattr(GeminiHinglishDrafter, "_init_client", lambda self: client)
    return GeminiHinglishDrafter()


def test_gemini_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(
        {
            "message": (
                "Namaste, aapka invoice INV-1029 ka Rs. 12,000 pending hai. "
                "Kya aap 5 din mein settle kar sakte hain? — Team RecoverOps"
            ),
            "suggested_promise_days": 5,
            "tone": "polite_reminder",
        }
    )
    d = _build_gemini(monkeypatch, client)
    out = d.draft(_ctx())
    assert isinstance(out, DraftedMessage)
    assert "INV-1029" in out.message
    assert out.suggested_promise_days == 5
    assert client.calls == 1


def test_gemini_falls_back_to_template_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    d = _build_gemini(monkeypatch, _FakeClient("not json at all"))
    out = d.draft(_ctx())
    # Template output — must contain the record id and amount.
    assert "INV-1029" in out.message


def test_gemini_falls_back_on_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Blowup:
        def generate_content(self, prompt: str):
            raise RuntimeError("429 quota exceeded")

    d = _build_gemini(monkeypatch, _Blowup())
    out = d.draft(_ctx())
    assert "INV-1029" in out.message


def test_factory_uses_template_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    d = get_hinglish_drafter("auto")
    assert isinstance(d, TemplateHinglishDrafter)


def test_factory_forces_template(monkeypatch: pytest.MonkeyPatch) -> None:
    d = get_hinglish_drafter("template")
    assert isinstance(d, TemplateHinglishDrafter)
