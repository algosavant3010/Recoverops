"""Data loading + caching for the dashboard."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from recoverops.data.generator import read_jsonl
from recoverops.models import AtRiskRecord, PromiseToPay
from recoverops.observability.audit import read_events

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(show_spinner=False)
def load_eval_report(path: str) -> dict[str, Any] | None:
    p = ROOT / path
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_audit_events(path: str) -> list[dict[str, Any]]:
    p = ROOT / path
    if not p.exists():
        return []
    return read_events(p)


@st.cache_data(show_spinner=False)
def load_records(path: str) -> list[dict[str, Any]]:
    p = ROOT / path
    if not p.exists():
        return []
    records: list[AtRiskRecord] = list(read_jsonl(p))
    return [r.model_dump(mode="json") for r in records]


@st.cache_data(show_spinner=False)
def load_promises(path: str) -> list[dict[str, Any]]:
    p = ROOT / path
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(PromiseToPay.model_validate_json(line).model_dump(mode="json"))
    return out


def load_outreach_events_from_log(path: str) -> list[dict[str, Any]]:
    """Extract the drafted-message payloads for the promise inbox."""
    return [e["payload"] for e in load_audit_events(path) if e["stage"] == "outreach_drafted"]


def paise_to_inr(paise: int | float) -> str:
    """Format paise as Indian rupees with lakhs/crores grouping."""
    if paise is None:
        return "—"
    rupees = paise / 100
    if rupees >= 1_00_00_000:
        return f"₹{rupees/1_00_00_000:.2f} Cr"
    if rupees >= 1_00_000:
        return f"₹{rupees/1_00_000:.2f} L"
    return f"₹{rupees:,.0f}"


def paise_to_inr_precise(paise: int | float) -> str:
    if paise is None:
        return "—"
    return f"₹{paise/100:,.2f}"
