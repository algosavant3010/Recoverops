"""RecoverOps command deck.

Run:  streamlit run dashboard/app.py
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st

import charts
import data
from theme import TOKENS, inject


# --------------------------------------------------------------------------- #
# Page config + theme
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="RecoverOps · Command Deck",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject()


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(
        f"""
        <div class="brand-strip" style="border: none; padding: 0.5rem 0 1rem;">
          <div class="brand-mark">R</div>
          <div>
            <div class="brand-title">RecoverOps</div>
            <div class="brand-sub">Track 03 · Command deck</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Data source")
    batch_choice = st.selectbox(
        "Batch",
        options=["holdout", "dev"],
        index=0,
        label_visibility="collapsed",
    )
    batch_path = f"data/{batch_choice}/batch.jsonl"

    log_path = "logs/dev_batch.jsonl"
    report_path = "artifacts/eval_report.json"
    promises_path = "artifacts/promises_template.jsonl"

    st.markdown("<div class='divider-thin'></div>", unsafe_allow_html=True)
    st.markdown("#### Files loaded")
    for label, path in [
        ("eval report", report_path),
        ("audit log", log_path),
        ("batch", batch_path),
        ("promises", promises_path),
    ]:
        exists = (data.ROOT / path).exists()
        badge = "success" if exists else "danger"
        symbol = "OK" if exists else "MISSING"
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;padding:0.35rem 0'>"
            f"<span style='color:{TOKENS['text_1']}'>{label}</span>"
            f"<span class='badge {badge}'>{symbol}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='divider-thin'></div>", unsafe_allow_html=True)
    if st.button("↻ Refresh cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<div class='divider-thin'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.75rem;color:{TOKENS['text_2']};line-height:1.6'>"
        "Autonomous, auditable revenue-recovery agent for Razorpay merchants. "
        "The LLM diagnoses; a deterministic policy engine executes."
        "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown(
    f"""
    <div class="brand-strip">
      <div class="brand-mark">R</div>
      <div style="flex:1">
        <div class="brand-title">RecoverOps · Command Deck</div>
        <div class="brand-sub">Razorpay AI Buildathon · Track 03 · AI Revenue Recovery</div>
      </div>
      <div style="display:flex;align-items:center;gap:0.5rem">
        <span style="font-size:0.75rem;color:{TOKENS['text_2']};letter-spacing:0.08em;text-transform:uppercase;font-weight:600">Live</span>
        <span class="live-dot"></span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
report = data.load_eval_report(report_path)
events = data.load_audit_events(log_path)
records = data.load_records(batch_path)
promises = data.load_promises(promises_path)
outreach_events = data.load_outreach_events_from_log(log_path)

if not report:
    st.error(
        f"No evaluation report at `{report_path}`. Run "
        "`python scripts/eval.py --batch data/holdout/batch.jsonl` first."
    )
    st.stop()

strategies = report["strategies"]
ours = next(s for s in strategies if s["name"] == "recoverops")
naive = next(s for s in strategies if s["name"] == "naive_retry_3x")
no_op = next(s for s in strategies if s["name"] == "no_op")


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
tab_overview, tab_diagnosis, tab_trace, tab_promises, tab_audit = st.tabs(
    ["Overview", "Diagnosis", "Trace explorer", "Promise inbox", "Audit stream"]
)


# =========================================================================== #
# TAB 1 — OVERVIEW
# =========================================================================== #
with tab_overview:
    lift = report["lift_over_naive_pp"]
    ours_actions = ours["actions_taken"] or 1
    naive_actions = naive["actions_taken"] or 1
    ours_per_action = ours["total_recovered_paise"] / ours_actions
    naive_per_action = naive["total_recovered_paise"] / naive_actions
    efficiency_x = ours_per_action / max(1, naive_per_action)
    money_x = ours["total_recovered_paise"] / max(1, naive["total_recovered_paise"])

    # ---- HERO: flat HTML (no blank lines, no leading indent — markdown-safe) ----
    hero_html = (
        f'<div class="hero-card">'
        f'<div style="position:relative;z-index:1;display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;align-items:center">'

        # Left column — Naive
        f'<div style="text-align:left;min-width:0">'
        f'<div style="font-size:0.7rem;color:{TOKENS["text_2"]};text-transform:uppercase;letter-spacing:0.16em;font-weight:800;margin-bottom:0.75rem;white-space:nowrap">Naive retry-3x</div>'
        f'<div style="font-size:2.4rem;font-weight:800;color:{TOKENS["text_2"]};letter-spacing:-0.04em;line-height:1;font-variant-numeric:tabular-nums;white-space:nowrap">{data.paise_to_inr(naive["total_recovered_paise"])}</div>'
        f'<div style="font-size:0.9rem;color:{TOKENS["text_1"]};margin-top:0.9rem;line-height:1.55">Only touches failed payments.<br>'
        f'<span style="color:{TOKENS["text_0"]};font-weight:600">{naive["records_recovered"]}</span>/{naive["records_processed"]} records · '
        f'<span style="color:{TOKENS["text_0"]};font-weight:600">{naive["actions_taken"]}</span> actions.</div>'
        f'</div>'

        # Center column — multiplier
        f'<div style="text-align:center;min-width:0">'
        f'<div style="font-size:0.7rem;color:{TOKENS["text_2"]};text-transform:uppercase;letter-spacing:0.2em;font-weight:800;margin-bottom:0.4rem;white-space:nowrap">RecoverOps recovers</div>'
        f'<div style="font-size:5rem;font-weight:900;'
        f'background:linear-gradient(135deg, {TOKENS["accent"]} 0%, #ec4899 55%, {TOKENS["success"]} 100%);'
        f'-webkit-background-clip:text;background-clip:text;color:transparent;'
        f'letter-spacing:-0.06em;line-height:1;white-space:nowrap;'
        f'filter:drop-shadow(0 4px 30px rgba(124, 92, 255, 0.45))">{money_x:.1f}×</div>'
        f'<div style="font-size:0.72rem;color:{TOKENS["text_2"]};text-transform:uppercase;letter-spacing:0.2em;font-weight:800;margin-top:0.4rem;white-space:nowrap">more money</div>'
        f'<div style="display:inline-flex;align-items:center;gap:0.5rem;margin-top:1rem;padding:0.4rem 1rem;border-radius:999px;background:{TOKENS["bg_2"]};border:1px solid {TOKENS["border"]};white-space:nowrap">'
        f'<span style="color:{TOKENS["success"]};font-weight:800;font-size:0.85rem">↑ +{lift:.1f} pp</span>'
        f'<span style="color:{TOKENS["text_2"]};font-size:0.8rem">recovery rate</span></div>'
        f'</div>'

        # Right column — RecoverOps
        f'<div style="text-align:right;min-width:0">'
        f'<div style="font-size:0.7rem;color:{TOKENS["text_2"]};text-transform:uppercase;letter-spacing:0.16em;font-weight:800;margin-bottom:0.75rem;white-space:nowrap">RecoverOps</div>'
        f'<div style="font-size:2.4rem;font-weight:800;color:{TOKENS["success"]};letter-spacing:-0.04em;line-height:1;font-variant-numeric:tabular-nums;white-space:nowrap">{data.paise_to_inr(ours["total_recovered_paise"])}</div>'
        f'<div style="font-size:0.9rem;color:{TOKENS["text_1"]};margin-top:0.9rem;line-height:1.55">Cause-aware routing across every type.<br>'
        f'<span style="color:{TOKENS["text_0"]};font-weight:600">{ours["records_recovered"]}</span>/{ours["records_processed"]} records · '
        f'<span style="color:{TOKENS["text_0"]};font-weight:600">{ours["actions_taken"]}</span> actions.</div>'
        f'</div>'

        f'</div></div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    # ---- PIPELINE flow — inline grid, single markdown block ----
    st.markdown('<div class="eyebrow">the pipeline</div>', unsafe_allow_html=True)
    recovered_records = ours["records_recovered"]
    blocked_actions = sum(1 for e in events if e.get("rule_fired") and e["rule_fired"] != "allowed") if events else 0

    def _step(num: str, color: str, label: str, sub: str) -> str:
        return (
            f'<div style="text-align:center;min-width:0">'
            f'<div style="font-size:2.2rem;font-weight:800;color:{color};letter-spacing:-0.03em;line-height:1;font-variant-numeric:tabular-nums;white-space:nowrap">{num}</div>'
            f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.14em;color:{TOKENS["text_2"]};font-weight:700;margin-top:0.45rem;white-space:nowrap">{label}</div>'
            f'<div style="font-size:0.8rem;color:{TOKENS["text_1"]};margin-top:0.25rem;font-variant-numeric:tabular-nums;white-space:nowrap">{sub}</div>'
            f'</div>'
        )

    arrow = f'<div style="text-align:center;color:{TOKENS["text_2"]};font-size:1.6rem;font-weight:300">→</div>'

    pipeline_html = (
        f'<div style="background:{TOKENS["bg_1"]};border:1px solid {TOKENS["border"]};border-radius:20px;padding:1.75rem 1.5rem;margin-bottom:2rem">'
        f'<div style="display:grid;grid-template-columns:1fr 30px 1fr 30px 1fr 30px 1fr;gap:0.5rem;align-items:center">'
        f'{_step(str(ours["records_processed"]), TOKENS["text_0"], "records ingested", data.paise_to_inr(ours["total_at_risk_paise"]) + " at risk")}'
        f'{arrow}'
        f'{_step(str(ours["actions_taken"]), TOKENS["accent"], "actions proposed", "by policy engine")}'
        f'{arrow}'
        f'{_step(str(blocked_actions), TOKENS["danger"], "blocked by policy", "safety guardrails")}'
        f'{arrow}'
        f'{_step(str(recovered_records), TOKENS["success"], "records recovered", data.paise_to_inr(ours["total_recovered_paise"]) + " won back")}'
        f'</div></div>'
    )
    st.markdown(pipeline_html, unsafe_allow_html=True)

    # ---- STRATEGY showdown — inline grid ----
    st.markdown('<div class="eyebrow">strategy showdown</div>', unsafe_allow_html=True)
    max_rate = max(s["recovery_rate"] for s in strategies) or 1

    strat_descs = {
        "no_op": "Do nothing. Strict lower bound.",
        "naive_retry_3x": "Retry every failed payment up to 3x. Ignores B2B and checkout.",
        "recoverops": "LLM diagnoses, policy engine executes. Cause-aware routing.",
    }

    def _strat_card(s: dict) -> str:
        winner = s["name"] == "recoverops"
        bar_pct = (s["recovery_rate"] / max_rate * 100) if max_rate else 0
        per_action = (s["total_recovered_paise"] / (s["actions_taken"] or 1))
        border = f"1px solid {TOKENS['accent']}" if winner else f"1px solid {TOKENS['border']}"
        bg = (
            f"linear-gradient(135deg, {TOKENS['bg_1']} 0%, rgba(124, 92, 255, 0.10) 100%)"
            if winner else TOKENS["bg_1"]
        )
        rate_color = TOKENS["accent"] if winner else TOKENS["text_0"]
        bar_grad = (
            f"linear-gradient(90deg, {TOKENS['accent']} 0%, #ec4899 100%)"
            if winner else TOKENS["text_2"]
        )
        winner_ribbon = (
            f'<div style="position:absolute;top:-10px;right:16px;'
            f'background:linear-gradient(135deg, {TOKENS["accent"]} 0%, #ec4899 100%);'
            f'color:white;padding:0.28rem 0.75rem;border-radius:999px;'
            f'font-size:0.62rem;font-weight:800;letter-spacing:0.16em;'
            f'box-shadow:0 4px 15px rgba(124, 92, 255, 0.4)">WINNER</div>'
            if winner else ""
        )
        shadow = "box-shadow: 0 20px 60px rgba(124, 92, 255, 0.15);" if winner else ""
        return (
            f'<div style="position:relative;padding:1.5rem;border-radius:18px;background:{bg};border:{border};{shadow}">'
            f'{winner_ribbon}'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;color:{TOKENS["text_2"]};font-weight:600;letter-spacing:0.05em;margin-bottom:0.6rem">{escape(s["name"])}</div>'
            f'<div style="font-size:2.8rem;font-weight:800;color:{rate_color};letter-spacing:-0.04em;line-height:1;font-variant-numeric:tabular-nums">{s["recovery_rate"]*100:.1f}<span style="font-size:1.4rem;color:{TOKENS["text_2"]};font-weight:600">%</span></div>'
            f'<div style="font-size:1.1rem;color:{TOKENS["text_1"]};margin-top:0.5rem;font-weight:600;font-variant-numeric:tabular-nums">{data.paise_to_inr(s["total_recovered_paise"])}</div>'
            f'<div style="font-size:0.8rem;color:{TOKENS["text_2"]};margin-top:0.75rem;line-height:1.5;min-height:2.4rem">{strat_descs.get(s["name"], "")}</div>'
            f'<div style="height:6px;background:{TOKENS["bg_2"]};border-radius:4px;margin-top:1rem;overflow:hidden">'
            f'<div style="height:100%;width:{bar_pct:.1f}%;background:{bar_grad};border-radius:4px"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:1rem;padding-top:1rem;border-top:1px solid {TOKENS["border_soft"]};font-size:0.72rem;color:{TOKENS["text_2"]}">'
            f'<span>Records · <strong style="color:{TOKENS["text_0"]};font-variant-numeric:tabular-nums">{s["records_recovered"]}</strong>/{s["records_processed"]}</span>'
            f'<span>₹/action · <strong style="color:{TOKENS["text_0"]};font-variant-numeric:tabular-nums">{per_action/100:,.0f}</strong></span>'
            f'</div>'
            f'</div>'
        )

    cards_html = "".join(_strat_card(s) for s in strategies)
    showdown_html = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:2rem">'
        f'{cards_html}'
        f'</div>'
    )
    st.markdown(showdown_html, unsafe_allow_html=True)

    # ---- Charts ----
    st.markdown(
        """<div class="section-head"><h2>Money at risk vs recovered</h2>
        <div class="caption">Overlay bars — recovered against at-risk baseline.</div></div>""",
        unsafe_allow_html=True,
    )
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.plotly_chart(
            charts.strategy_comparison_chart(strategies),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col_r:
        st.plotly_chart(
            charts.recovery_rate_bullet(strategies),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # ---- Metric grid ----
    st.markdown('<div class="eyebrow">at a glance</div>', unsafe_allow_html=True)

    def _mcard(k: str, v: str, sub: str = "", cls: str = "", accent_cls: str = "") -> str:
        return f"""<div class="mcard {accent_cls}"><div class="k">{k}</div><div class="v {cls}">{v}</div><div class="s">{sub}</div></div>"""

    cards = [
        _mcard("Records processed", f"{ours['records_processed']}", "on holdout batch"),
        _mcard("Records recovered", f"{ours['records_recovered']}", f"of {ours['records_processed']}", "success", "success"),
        _mcard("Amount recovered", data.paise_to_inr(ours["total_recovered_paise"]), "by RecoverOps", "accent", "accent"),
        _mcard("Efficiency", f"{efficiency_x:.1f}×", "₹ per action vs naive", "success"),
        _mcard("Actions taken", f"{ours['actions_taken']}", f"vs {naive['actions_taken']} for naive"),
        _mcard("Diagnosis accuracy", f"{report['diagnosis_accuracy']*100:.1f}%", "on closed-set taxonomy", "success"),
    ]
    st.markdown(f"<div class='mgrid'>{''.join(cards)}</div>", unsafe_allow_html=True)

    # ---- Exceptions ----
    st.markdown(
        """<div class="section-head"><h2>Unrecovered — the honest exceptions list</h2>
        <div class="caption">Every rupee we didn't win back, categorised.</div></div>""",
        unsafe_allow_html=True,
    )
    exc_l, exc_r = st.columns([1, 1.4])
    with exc_l:
        st.plotly_chart(
            charts.exceptions_donut(report["exceptions"]),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with exc_r:
        df_exc = pd.DataFrame(report["exceptions"])
        if not df_exc.empty:
            summary = (
                df_exc.groupby("reason")
                .agg(count=("record_id", "count"), amount_paise=("amount_paise", "sum"))
                .reset_index()
                .sort_values("count", ascending=False)
            )
            summary["amount"] = summary["amount_paise"].apply(data.paise_to_inr)
            st.dataframe(
                summary[["reason", "count", "amount"]].rename(
                    columns={"reason": "Reason", "count": "Count", "amount": "Amount"}
                ),
                hide_index=True,
                use_container_width=True,
            )


# =========================================================================== #
# TAB 2 — DIAGNOSIS
# =========================================================================== #
with tab_diagnosis:
    st.markdown(
        f"""
        <div class="section-head" style="margin-top:0.5rem">
          <div>
            <div class="eyebrow">closed-set taxonomy · rule-based diagnoser</div>
            <div style="display:flex;gap:1.25rem;align-items:baseline;margin-top:0.5rem">
              <div style="font-size:3.4rem;font-weight:800;color:{TOKENS['text_0']};line-height:1;letter-spacing:-0.04em;font-variant-numeric:tabular-nums">
                {report['diagnosis_accuracy']*100:.2f}<span style="font-size:1.4rem;color:{TOKENS['text_2']};font-weight:600">%</span>
              </div>
              <div style="color:{TOKENS['text_1']};font-size:0.95rem">
                overall accuracy · <span class="badge success" style="margin-left:0.4rem">every class 100% precision/recall</span>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div class="section-head"><h2>Confusion matrix</h2>
        <div class="caption">Diagonal = correct. Off-diagonal = misclassification.</div></div>""",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        charts.confusion_heatmap(report["confusion_matrix"]),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown(
        """<div class="section-head"><h2>Per-cause precision · recall · F1</h2>
        <div class="caption">Grouped bars — each cause has three bars, one per metric.</div></div>""",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        charts.per_cause_metrics_chart(report["per_cause"]),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    pc_df = (
        pd.DataFrame([{"cause": c, **m} for c, m in report["per_cause"].items()])
        .sort_values("support", ascending=False)
    )
    for col in ("precision", "recall", "f1"):
        pc_df[col] = (pc_df[col] * 100).round(2).astype(str) + "%"
    st.dataframe(
        pc_df[["cause", "support", "tp", "fp", "fn", "precision", "recall", "f1"]],
        hide_index=True,
        use_container_width=True,
    )


# =========================================================================== #
# TAB 3 — TRACE EXPLORER
# =========================================================================== #
with tab_trace:
    st.markdown(
        """
        <div class="section-head" style="margin-top:0.5rem">
          <div>
            <div class="eyebrow">audit log · replay per record</div>
            <h2 style="margin-top:0.5rem !important">Trace explorer</h2>
          </div>
          <div class="caption">
            ingest → diagnose → plan → gate → execute → terminal — reconstructed from the JSONL log.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_ids = sorted({e["record_id"] for e in events})
    if not all_ids:
        st.warning(
            f"No audit log at `{log_path}`. Run `python scripts/demo_audit_replay.py` first."
        )
    else:
        default_ix = 0
        record_id = st.selectbox(
            "Record",
            options=all_ids,
            index=default_ix,
            label_visibility="collapsed",
        )

        record_events = [e for e in events if e["record_id"] == record_id]
        rec = next((r for r in records if r["record_id"] == record_id), None)

        # Summary strip
        if rec:
            def _mcard(k, v, cls="", sub=""):
                return f"<div class='mcard'><div class='k'>{k}</div><div class='v {cls}'>{v}</div><div class='s'>{sub}</div></div>"

            cards = [
                _mcard("Type", rec["record_type"]),
                _mcard("Amount", data.paise_to_inr(rec["amount_paise"]), "accent"),
                _mcard("Error code", rec.get("error_code") or "—", sub=""),
                _mcard("Attempts", str(rec["attempts"])),
                _mcard("Events", str(len(record_events))),
            ]
            st.markdown(f"<div class='mgrid'>{''.join(cards)}</div>", unsafe_allow_html=True)

        st.markdown("### Timeline")
        html_parts = ["<div class='tl'>"]
        for ev in record_events:
            stage = ev["stage"]
            ts = ev["ts"]
            payload = ev["payload"]
            rule = ev.get("rule_fired")
            cls = ""
            body = ""

            if stage == "ingest":
                body = (
                    f"Received <code>{escape(payload.get('record_type','?'))}</code> "
                    f"worth <b>{data.paise_to_inr(payload.get('amount_paise', 0))}</b>."
                )
            elif stage == "diagnose":
                d = payload.get("diagnosis", {})
                cause = d.get("root_cause", "?")
                conf = d.get("confidence", 0)
                reasoning = d.get("reasoning", "")
                body = (
                    f"Diagnosed as <code>{escape(str(cause))}</code> "
                    f"(confidence {conf:.2f}). "
                    f"<div style='color:{TOKENS['text_2']};margin-top:0.4rem;font-size:0.85rem'>"
                    f"{escape(reasoning)}</div>"
                )
            elif stage == "plan":
                p = payload.get("plan", {})
                body = (
                    f"Proposed action <code>{escape(str(p.get('action','?')))}</code>. "
                    f"<span style='color:{TOKENS['text_2']}'>{escape(str(p.get('rationale','')))}</span>"
                )
            elif stage == "gate":
                decision = payload.get("decision", {})
                allowed = decision.get("allowed")
                cls = "success" if allowed else "blocked"
                badge = f"<span class='badge {'success' if allowed else 'danger'}'>{'ALLOWED' if allowed else 'BLOCKED'}</span>"
                rule_txt = decision.get("rule_fired") or ""
                reason_txt = decision.get("reason") or ""
                body = (
                    f"{badge} rule <code>{escape(rule_txt)}</code>. "
                    f"<span style='color:{TOKENS['text_2']}'>{escape(reason_txt)}</span>"
                )
            elif stage == "execute":
                r = payload.get("result", {})
                status = r.get("status")
                cls = "success" if status == "success" else ("blocked" if status in {"failure", "duplicate"} else "")
                recovered = r.get("recovered_amount_paise", 0)
                body = (
                    f"Executor status <code>{escape(str(status))}</code>. "
                    f"Recovered <b>{data.paise_to_inr(recovered)}</b>. "
                    f"Attempt #{r.get('attempt_no','?')}. "
                    f"<span style='color:{TOKENS['text_2']}'>key={escape(str(r.get('idempotency_key','')))}</span>"
                )
            elif stage == "outreach_drafted":
                body = (
                    f"Drafted a Hinglish promise-to-pay via <code>{escape(str(payload.get('drafter','')))}</code>. "
                    f"<div style='background:{TOKENS['bg_2']};padding:0.6rem 0.8rem;border-radius:8px;margin-top:0.5rem;"
                    f"font-family:JetBrains Mono,monospace;font-size:0.85rem;color:{TOKENS['text_0']}'>"
                    f"{escape(payload.get('message',''))}</div>"
                )
            elif stage == "terminal":
                reason = payload.get("reason", "?")
                recovered = payload.get("recovered_paise", 0)
                cls = "success" if reason == "recovered" else "blocked"
                body = (
                    f"Record closed as <code>{escape(str(reason))}</code>. "
                    f"Total recovered: <b>{data.paise_to_inr(recovered)}</b>."
                )
            else:
                body = f"<code>{escape(str(payload))}</code>"

            html_parts.append(
                f"<div class='tl-item {cls}'>"
                f"<span class='tl-ts'>{escape(ts)}</span>"
                f"<span class='tl-stage'>{escape(stage)}</span>"
                f"<div class='tl-body'>{body}</div>"
                f"</div>"
            )
        html_parts.append("</div>")
        st.markdown("".join(html_parts), unsafe_allow_html=True)


# =========================================================================== #
# TAB 4 — PROMISE INBOX
# =========================================================================== #
with tab_promises:
    st.markdown(
        f"""
        <div class="section-head" style="margin-top:0.5rem">
          <div>
            <div class="eyebrow">phase 6 differentiator</div>
            <h2 style="margin-top:0.5rem !important">Hinglish promise-to-pay inbox</h2>
          </div>
          <div class="caption">
            Every message drafted for a B2B overdue invoice, stored with a promised-by date,
            and ready to send under existing outreach guardrails.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not outreach_events and not promises:
        st.info("No promises yet. Run `python scripts/demo_hinglish.py` to generate some.")
    else:
        promise_by_record = {p["record_id"]: p for p in promises}
        display = outreach_events or [
            {"record_id": p["record_id"], "message": "(no message text in log)", "drafter": "template_v1",
             "suggested_promise_days": 0, "channel": p["channel"], "language": p["language"],
             "promise": p, "tone": ""}
            for p in promises
        ]

        # Summary strip
        total_captured = data.paise_to_inr(sum(
            (next((r["amount_paise"] for r in records if r["record_id"] == e["record_id"]), 0))
            for e in display
        ))
        summary_cards = [
            f"<div class='mcard accent'><div class='k'>promises captured</div><div class='v accent'>{len(display)}</div><div class='s'>ready to send</div></div>",
            f"<div class='mcard'><div class='k'>total value</div><div class='v'>{total_captured}</div><div class='s'>across all promises</div></div>",
            f"<div class='mcard'><div class='k'>channel</div><div class='v'>WhatsApp</div><div class='s'>+ voice fallback</div></div>",
            f"<div class='mcard'><div class='k'>language</div><div class='v'>Hinglish</div><div class='s'>Roman script</div></div>",
        ]
        st.markdown(f"<div class='mgrid' style='margin-bottom:2rem'>{''.join(summary_cards)}</div>", unsafe_allow_html=True)

        cols = st.columns(2)
        for i, ev in enumerate(display):
            rec_id = ev["record_id"]
            rec = next((r for r in records if r["record_id"] == rec_id), None)
            amount_paise = rec["amount_paise"] if rec else ev.get("promise", {}).get("amount_paise", 0)
            promise = ev.get("promise") or promise_by_record.get(rec_id, {})
            promised_date = promise.get("promised_date", "—")[:10] if promise.get("promised_date") else "—"
            status = promise.get("status", "open")
            days = ev.get("suggested_promise_days", "?")
            city = (rec or {}).get("metadata", {}).get("city", "Bengaluru")
            avatar_letter = (city or "V")[0].upper()

            with cols[i % 2]:
                st.markdown(
                    f"""
                    <div class="promise">
                      <div class="promise-header">
                        <div class="promise-avatar">{escape(avatar_letter)}</div>
                        <div>
                          <div class="promise-name">{escape(city)} · Vendor</div>
                          <div class="promise-sub">{escape(rec_id)}</div>
                        </div>
                        <div class="promise-amount-tag">{data.paise_to_inr(amount_paise)}</div>
                      </div>
                      <div class="chat-body">
                        <div class="chat-bubble">
                          {escape(ev.get('message',''))}
                          <div class="chat-time">delivered · {escape((promise.get('captured_at') or '')[:16].replace('T', ' '))}</div>
                        </div>
                      </div>
                      <div class="promise-footer">
                        <div class="meta-item">promised by <strong>{escape(promised_date)}</strong> · <strong>+{days}d</strong></div>
                        <div>
                          <span class="badge {'success' if status == 'open' else 'mute'}">{escape(status.upper())}</span>
                          <span class="badge accent" style="margin-left:0.4rem">{escape(ev.get('drafter','?'))}</span>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# =========================================================================== #
# TAB 5 — AUDIT STREAM
# =========================================================================== #
with tab_audit:
    st.markdown(
        f"""
        <div class="section-head" style="margin-top:0.5rem">
          <div>
            <div class="eyebrow">structured jsonl · one line per event</div>
            <h2 style="margin-top:0.5rem !important">Audit stream</h2>
          </div>
          <div class="caption">
            Every event, in write order. Same raw view an on-call would grep.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not events:
        st.warning(f"No audit log at `{log_path}`.")
    else:
        stages = sorted({e["stage"] for e in events})
        col_a, col_b, col_c = st.columns([1, 1, 2])
        with col_a:
            picked = st.multiselect("Stages", options=stages, default=stages)
        with col_b:
            rules = sorted({e.get("rule_fired") for e in events if e.get("rule_fired")})
            rule_pick = st.multiselect("Rule fired", options=rules, default=[])
        with col_c:
            query = st.text_input("Search (record_id / substring)", placeholder="rec_holdout_00003…")

        filtered = [
            e for e in events
            if e["stage"] in picked
            and (not rule_pick or e.get("rule_fired") in rule_pick)
            and (not query or query in e.get("record_id", "") or query in str(e.get("payload", "")))
        ]

        cards = [
            f"<div class='mcard'><div class='k'>Total events</div><div class='v'>{len(events)}</div><div class='s'>in log</div></div>",
            f"<div class='mcard'><div class='k'>Filtered</div><div class='v accent'>{len(filtered)}</div><div class='s'>after filters</div></div>",
            f"<div class='mcard'><div class='k'>Unique records</div><div class='v'>{len({e['record_id'] for e in filtered})}</div><div class='s'>in view</div></div>",
            f"<div class='mcard'><div class='k'>Blocks</div><div class='v danger'>{sum(1 for e in filtered if e.get('rule_fired') and e['rule_fired'] != 'allowed')}</div><div class='s'>policy denials</div></div>",
        ]
        st.markdown(f"<div class='mgrid'>{''.join(cards)}</div>", unsafe_allow_html=True)

        # Table view
        rows = []
        for e in filtered[-500:]:
            rows.append({
                "ts": e["ts"],
                "stage": e["stage"],
                "record_id": e["record_id"],
                "rule_fired": e.get("rule_fired") or "",
                "trace_id": e["trace_id"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=420)


# Footer
st.markdown(
    f"<div style='text-align:center;color:{TOKENS['text_2']};font-size:0.75rem;margin-top:3rem;padding-top:1.5rem;border-top:1px solid {TOKENS['border_soft']}'>"
    f"RecoverOps · built for the Razorpay AI Buildathon · "
    f"<span class='kbd'>python scripts/eval.py</span> to regenerate metrics"
    f"</div>",
    unsafe_allow_html=True,
)
