"""Gemini diagnoser tests — SDK is fully mocked, no network calls."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from recoverops.models import AtRiskRecord
from recoverops.reasoning.signals import signals_from_record
from recoverops.taxonomy import RecordType, RootCause


def _record() -> AtRiskRecord:
    return AtRiskRecord(
        record_id="rec_test_000001",
        record_type=RecordType.FAILED_PAYMENT,
        merchant_id="acc_ABCD1234",
        customer_id="cust_9",
        amount_paise=50_000,
        error_code="GATEWAY_ERROR:issuer_down",
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


class _FakeClient:
    def __init__(self, payload: dict | str) -> None:
        self._payload = payload if isinstance(payload, str) else json.dumps(payload)
        self.calls = 0

    def generate_content(self, prompt: str) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(text=self._payload)


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def _build(monkeypatch: pytest.MonkeyPatch, client: _FakeClient):
    from recoverops.reasoning import gemini

    monkeypatch.setattr(gemini.GeminiDiagnoser, "_init_client", lambda self: client)
    return gemini.GeminiDiagnoser()


def test_happy_path_parses_valid_output(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(
        {
            "root_cause": "gateway_downtime",
            "confidence": 0.82,
            "reasoning": "issuer_down error code",
            "signals_used": ["error_code"],
        }
    )
    diag = _build(monkeypatch, client)
    d = diag.diagnose(signals_from_record(_record()))
    assert d.root_cause is RootCause.GATEWAY_DOWNTIME
    assert 0.8 <= d.confidence <= 0.9
    assert client.calls == 1


def test_out_of_taxonomy_label_falls_back_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(
        {
            "root_cause": "made_up_reason",
            "confidence": 0.9,
            "reasoning": "n/a",
            "signals_used": [],
        }
    )
    diag = _build(monkeypatch, client)
    d = diag.diagnose(signals_from_record(_record()))
    assert d.root_cause is RootCause.UNKNOWN
    assert d.confidence == 0.0
    assert d.reasoning.startswith("gemini_fallback:")


def test_schema_invalid_output_falls_back_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient("this is not json")
    diag = _build(monkeypatch, client)
    d = diag.diagnose(signals_from_record(_record()))
    assert d.root_cause is RootCause.UNKNOWN
    assert d.confidence == 0.0


def test_cache_avoids_repeat_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(
        {
            "root_cause": "gateway_downtime",
            "confidence": 0.82,
            "reasoning": "cached",
            "signals_used": ["error_code"],
        }
    )
    diag = _build(monkeypatch, client)
    signals = signals_from_record(_record())
    diag.diagnose(signals)
    diag.diagnose(signals)
    assert client.calls == 1, "identical signals should hit the cache"


def test_prompt_never_contains_ground_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Belt-and-braces: even if a caller misuses the API, the rendered prompt
    must not contain ground-truth or PII strings."""
    captured: dict[str, str] = {}

    class _Capture(_FakeClient):
        def generate_content(self, prompt: str) -> SimpleNamespace:
            captured["prompt"] = prompt
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "root_cause": "gateway_downtime",
                        "confidence": 0.5,
                        "reasoning": "ok",
                        "signals_used": [],
                    }
                )
            )

    diag = _build(monkeypatch, _Capture({}))
    diag.diagnose(signals_from_record(_record()))
    rendered = captured["prompt"]
    for banned in ("true_root_cause", "true_recover_prob", "customer_id", "cust_9"):
        assert banned not in rendered, f"prompt leaked: {banned}"


def test_factory_returns_rules_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("RECOVEROPS_DIAGNOSER", "auto")
    from recoverops.reasoning.factory import get_diagnoser
    from recoverops.reasoning.rules import RuleBasedDiagnoser

    d = get_diagnoser()
    assert isinstance(d, RuleBasedDiagnoser)


def test_factory_forces_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    from recoverops.reasoning.factory import get_diagnoser
    from recoverops.reasoning.rules import RuleBasedDiagnoser

    assert isinstance(get_diagnoser("rules"), RuleBasedDiagnoser)
