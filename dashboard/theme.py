"""Design system: CSS injection + tokens.

We treat the dashboard like a design surface, not a Streamlit form. Every
number is typography, every card is a data-density unit. Dark mode by
default because engineers judge dashboards on grids, not on gradients.
"""
from __future__ import annotations

import streamlit as st


TOKENS = {
    "bg_0": "#07090f",
    "bg_1": "#0d1220",
    "bg_2": "#131a2e",
    "border": "#1f2740",
    "border_soft": "#161d31",
    "text_0": "#f4f6fb",
    "text_1": "#c1c8db",
    "text_2": "#7d879e",
    "accent": "#7c5cff",
    "accent_soft": "rgba(124, 92, 255, 0.15)",
    "success": "#34d399",
    "success_soft": "rgba(52, 211, 153, 0.14)",
    "warn": "#f59e0b",
    "warn_soft": "rgba(245, 158, 11, 0.14)",
    "danger": "#f87171",
    "danger_soft": "rgba(248, 113, 113, 0.14)",
    "info": "#60a5fa",
}


def inject() -> None:
    """Push the entire design system into the page as one CSS blob."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

/* ---------- root ---------- */
html, body, [data-testid="stAppViewContainer"] {{
    background: {TOKENS['bg_0']} !important;
    color: {TOKENS['text_0']} !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-feature-settings: "cv11", "ss01";
    -webkit-font-smoothing: antialiased;
}}

[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stAppViewContainer"] > .main {{
    background:
        radial-gradient(1400px 700px at 5% -10%, {TOKENS['accent_soft']} 0%, transparent 55%),
        radial-gradient(1000px 500px at 100% 0%, rgba(96, 165, 250, 0.10) 0%, transparent 55%),
        radial-gradient(800px 400px at 50% 100%, rgba(52, 211, 153, 0.05) 0%, transparent 60%),
        {TOKENS['bg_0']};
}}

.block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1440px !important;
}}

[data-testid="stSidebar"] {{
    background: {TOKENS['bg_1']} !important;
    border-right: 1px solid {TOKENS['border_soft']} !important;
}}
[data-testid="stSidebar"] * {{ color: {TOKENS['text_1']} !important; }}

/* ---------- typography ---------- */
h1, h2, h3, h4, h5, h6 {{ color: {TOKENS['text_0']} !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }}
h1 {{ font-size: 2rem !important; }}
h2 {{ font-size: 1.35rem !important; margin-top: 2.5rem !important; margin-bottom: 1rem !important; }}
h3 {{ font-size: 1.05rem !important; }}
p, li, span, div {{ color: {TOKENS['text_1']}; }}
code, pre {{ font-family: 'JetBrains Mono', ui-monospace, monospace !important; }}

/* section eyebrow */
.eyebrow {{
    display: inline-flex; align-items: center; gap: 0.4rem;
    font-size: 0.7rem; letter-spacing: 0.15em; text-transform: uppercase;
    color: {TOKENS['text_2']}; font-weight: 600;
    margin-bottom: 0.6rem;
}}
.eyebrow::before {{
    content: ''; width: 20px; height: 2px; background: {TOKENS['accent']};
    display: inline-block; border-radius: 2px;
}}

/* ---------- brand strip ---------- */
.brand-strip {{
    display: flex; align-items: center; gap: 1rem;
    padding: 1rem 0 1.25rem;
    border-bottom: 1px solid {TOKENS['border_soft']};
    margin-bottom: 1.5rem;
}}
.brand-mark {{
    width: 46px; height: 46px; border-radius: 13px;
    background: linear-gradient(135deg, {TOKENS['accent']} 0%, #ec4899 100%);
    display: grid; place-items: center;
    color: white; font-weight: 800; font-size: 1.2rem;
    box-shadow: 0 10px 30px rgba(124, 92, 255, 0.35), inset 0 1px 0 rgba(255,255,255,0.2);
}}
.brand-title {{ font-size: 1.35rem; font-weight: 700; color: {TOKENS['text_0']}; letter-spacing: -0.02em; }}
.brand-sub {{ font-size: 0.78rem; color: {TOKENS['text_2']}; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; }}
.live-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: {TOKENS['success']}; margin-left: auto;
    box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6); animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6); }}
    70% {{ box-shadow: 0 0 0 10px rgba(52, 211, 153, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }}
}}

/* ---------- HERO: 3-column showdown ---------- */
.hero {{
    display: grid; grid-template-columns: 1fr auto 1fr; gap: 2rem;
    padding: 2.5rem 2rem;
    background:
        linear-gradient(135deg, rgba(124, 92, 255, 0.12) 0%, rgba(236, 72, 153, 0.06) 50%, rgba(52, 211, 153, 0.08) 100%),
        {TOKENS['bg_1']};
    border: 1px solid {TOKENS['border']};
    border-radius: 24px;
    margin-bottom: 2rem;
    position: relative; overflow: hidden;
    align-items: center;
}}
.hero::before {{
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(800px 400px at 100% 0%, {TOKENS['accent_soft']}, transparent 60%);
    pointer-events: none;
}}
.hero-side {{ position: relative; z-index: 1; }}
.hero-side.left {{ text-align: left; }}
.hero-side.right {{ text-align: right; }}
.hero-side .label {{ font-size: 0.72rem; color: {TOKENS['text_2']}; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 0.75rem; }}
.hero-side .value {{ font-size: 2.6rem; font-weight: 800; color: {TOKENS['text_0']}; letter-spacing: -0.04em; line-height: 1; font-variant-numeric: tabular-nums; }}
.hero-side .sub {{ font-size: 0.95rem; color: {TOKENS['text_1']}; margin-top: 0.75rem; line-height: 1.5; }}
.hero-side .value.muted {{ color: {TOKENS['text_2']}; }}
.hero-side .value.success {{ color: {TOKENS['success']}; }}

.hero-vs {{
    position: relative; z-index: 1;
    display: flex; flex-direction: column; align-items: center; gap: 0.5rem;
    padding: 0 1rem;
}}
.hero-vs .multiplier {{
    font-size: 5.5rem; font-weight: 900;
    background: linear-gradient(135deg, {TOKENS['accent']} 0%, #ec4899 60%, {TOKENS['success']} 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    letter-spacing: -0.06em; line-height: 1;
    filter: drop-shadow(0 4px 30px rgba(124, 92, 255, 0.4));
}}
.hero-vs .multiplier-tag {{
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.16em;
    color: {TOKENS['text_2']}; font-weight: 700; margin-top: 0.5rem;
}}
.hero-vs .arrow {{
    display: flex; align-items: center; gap: 0.5rem;
    font-size: 0.85rem; color: {TOKENS['text_2']}; font-weight: 500;
    padding: 0.4rem 1rem; background: {TOKENS['bg_2']};
    border: 1px solid {TOKENS['border']}; border-radius: 999px;
    margin-top: 0.75rem;
}}
.hero-vs .arrow .up {{ color: {TOKENS['success']}; font-weight: 700; }}

/* ---------- PIPELINE flow visualization ---------- */
.pipeline {{
    display: grid; grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr; gap: 0;
    align-items: stretch; padding: 1.5rem;
    background: {TOKENS['bg_1']}; border: 1px solid {TOKENS['border']}; border-radius: 20px;
    margin-bottom: 2rem;
}}
.pipe-step {{
    display: flex; flex-direction: column; align-items: center; gap: 0.4rem;
    padding: 0.5rem;
}}
.pipe-step .num {{ font-size: 1.8rem; font-weight: 800; color: {TOKENS['text_0']}; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }}
.pipe-step .num.accent {{ color: {TOKENS['accent']}; }}
.pipe-step .num.success {{ color: {TOKENS['success']}; }}
.pipe-step .num.danger  {{ color: {TOKENS['danger']}; }}
.pipe-step .num.warn    {{ color: {TOKENS['warn']}; }}
.pipe-step .lbl {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: {TOKENS['text_2']}; font-weight: 600; text-align: center; }}
.pipe-step .amt {{ font-size: 0.85rem; color: {TOKENS['text_1']}; font-variant-numeric: tabular-nums; margin-top: 0.15rem; }}
.pipe-arrow {{
    display: flex; align-items: center; justify-content: center;
    color: {TOKENS['text_2']}; font-size: 1.4rem;
    padding: 0 0.5rem;
}}

/* ---------- STRATEGY showdown cards ---------- */
.showdown {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem; }}
.strat {{
    padding: 1.5rem; border-radius: 18px;
    background: {TOKENS['bg_1']}; border: 1px solid {TOKENS['border']};
    position: relative; transition: transform 200ms, box-shadow 200ms;
}}
.strat:hover {{ transform: translateY(-3px); }}
.strat.winner {{
    background: linear-gradient(135deg, {TOKENS['bg_1']} 0%, rgba(124, 92, 255, 0.08) 100%);
    border: 1px solid {TOKENS['accent']};
    box-shadow: 0 20px 60px rgba(124, 92, 255, 0.15), inset 0 1px 0 rgba(255,255,255,0.05);
}}
.strat.winner::before {{
    content: 'WINNER';
    position: absolute; top: -10px; right: 16px;
    background: linear-gradient(135deg, {TOKENS['accent']} 0%, #ec4899 100%);
    color: white; padding: 0.25rem 0.7rem; border-radius: 999px;
    font-size: 0.65rem; font-weight: 800; letter-spacing: 0.14em;
    box-shadow: 0 4px 15px rgba(124, 92, 255, 0.4);
}}
.strat .name {{ font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: {TOKENS['text_2']}; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
.strat .rate {{ font-size: 2.8rem; font-weight: 800; color: {TOKENS['text_0']}; letter-spacing: -0.04em; line-height: 1; font-variant-numeric: tabular-nums; }}
.strat.winner .rate {{ color: {TOKENS['accent']}; }}
.strat .amount {{ font-size: 1.1rem; color: {TOKENS['text_1']}; margin-top: 0.5rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
.strat .desc {{ font-size: 0.82rem; color: {TOKENS['text_2']}; margin-top: 0.75rem; line-height: 1.5; }}
.strat .bar {{
    height: 6px; background: {TOKENS['bg_2']}; border-radius: 4px; margin-top: 1rem; overflow: hidden;
}}
.strat .bar > span {{
    display: block; height: 100%;
    background: linear-gradient(90deg, {TOKENS['text_2']} 0%, {TOKENS['text_2']} 100%);
    border-radius: 4px; transition: width 800ms cubic-bezier(0.4, 0, 0.2, 1);
}}
.strat.winner .bar > span {{ background: linear-gradient(90deg, {TOKENS['accent']} 0%, #ec4899 100%); }}
.strat .meta {{
    display: flex; justify-content: space-between; margin-top: 1rem;
    padding-top: 1rem; border-top: 1px solid {TOKENS['border_soft']};
    font-size: 0.75rem; color: {TOKENS['text_2']};
}}
.strat .meta strong {{ color: {TOKENS['text_0']}; font-variant-numeric: tabular-nums; }}

/* ---------- metric cards ---------- */
.mgrid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
.mcard {{
    padding: 1.25rem;
    background: {TOKENS['bg_1']};
    border: 1px solid {TOKENS['border']};
    border-radius: 14px;
    transition: border-color 200ms, transform 200ms;
    position: relative; overflow: hidden;
}}
.mcard::before {{
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: {TOKENS['border']}; transition: background 200ms;
}}
.mcard:hover {{ border-color: {TOKENS['accent']}; transform: translateY(-2px); }}
.mcard:hover::before {{ background: {TOKENS['accent']}; }}
.mcard .k {{ font-size: 0.7rem; color: {TOKENS['text_2']}; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }}
.mcard .v {{ font-size: 1.75rem; font-weight: 700; color: {TOKENS['text_0']}; margin-top: 0.4rem; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}
.mcard .s {{ font-size: 0.8rem; color: {TOKENS['text_2']}; margin-top: 0.25rem; }}
.mcard .v.success {{ color: {TOKENS['success']}; }}
.mcard .v.danger {{ color: {TOKENS['danger']}; }}
.mcard .v.accent {{ color: {TOKENS['accent']}; }}
.mcard.accent::before {{ background: {TOKENS['accent']}; }}
.mcard.success::before {{ background: {TOKENS['success']}; }}

/* ---------- badges ---------- */
.badge {{ display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.22rem 0.65rem; border-radius: 999px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; }}
.badge.success {{ background: {TOKENS['success_soft']}; color: {TOKENS['success']}; }}
.badge.danger  {{ background: {TOKENS['danger_soft']};  color: {TOKENS['danger']}; }}
.badge.warn    {{ background: {TOKENS['warn_soft']};    color: {TOKENS['warn']}; }}
.badge.info    {{ background: rgba(96, 165, 250, 0.14); color: {TOKENS['info']}; }}
.badge.mute    {{ background: rgba(125, 135, 158, 0.14); color: {TOKENS['text_2']}; }}
.badge.accent  {{ background: {TOKENS['accent_soft']};  color: {TOKENS['accent']}; }}

/* ---------- trace timeline ---------- */
.tl {{ position: relative; padding-left: 2rem; }}
.tl::before {{ content: ''; position: absolute; left: 12px; top: 8px; bottom: 8px; width: 2px; background: linear-gradient(to bottom, {TOKENS['border']} 0%, {TOKENS['border']} 100%); }}
.tl-item {{ position: relative; margin-bottom: 0.9rem; padding: 1rem 1.25rem; background: {TOKENS['bg_1']}; border: 1px solid {TOKENS['border']}; border-radius: 12px; transition: border-color 200ms; }}
.tl-item:hover {{ border-color: {TOKENS['accent']}; }}
.tl-item::before {{
    content: ''; position: absolute; left: -2rem; top: 1.15rem;
    width: 12px; height: 12px; border-radius: 50%;
    background: {TOKENS['accent']}; box-shadow: 0 0 0 4px {TOKENS['bg_0']}, 0 0 0 5px {TOKENS['accent']};
}}
.tl-item.blocked::before {{ background: {TOKENS['danger']}; box-shadow: 0 0 0 4px {TOKENS['bg_0']}, 0 0 0 5px {TOKENS['danger']}; }}
.tl-item.success::before {{ background: {TOKENS['success']}; box-shadow: 0 0 0 4px {TOKENS['bg_0']}, 0 0 0 5px {TOKENS['success']}; }}
.tl-stage {{ font-size: 0.68rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.16em; color: {TOKENS['text_2']}; }}
.tl-ts {{ font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: {TOKENS['text_2']}; float: right; }}
.tl-body {{ margin-top: 0.55rem; font-size: 0.9rem; color: {TOKENS['text_1']}; line-height: 1.55; }}
.tl-body code {{ background: {TOKENS['bg_2']}; padding: 0.12rem 0.45rem; border-radius: 6px; font-size: 0.82rem; color: {TOKENS['text_0']}; }}

/* ---------- WhatsApp promise mockup ---------- */
.promise {{
    background: linear-gradient(180deg, {TOKENS['bg_1']} 0%, {TOKENS['bg_2']} 100%);
    border: 1px solid {TOKENS['border']};
    border-radius: 20px; padding: 0; margin-bottom: 1.25rem;
    overflow: hidden; transition: transform 200ms, box-shadow 200ms;
}}
.promise:hover {{ transform: translateY(-3px); box-shadow: 0 20px 60px rgba(0,0,0,0.4); }}
.promise-header {{
    display: flex; align-items: center; gap: 0.75rem;
    padding: 0.9rem 1.2rem;
    background: rgba(0, 0, 0, 0.35);
    border-bottom: 1px solid {TOKENS['border_soft']};
}}
.promise-avatar {{
    width: 40px; height: 40px; border-radius: 50%;
    background: linear-gradient(135deg, #005c4b 0%, #007566 100%);
    display: grid; place-items: center;
    color: white; font-weight: 700; font-size: 0.95rem;
    box-shadow: 0 4px 12px rgba(0, 92, 75, 0.35);
}}
.promise-name {{ font-size: 0.9rem; font-weight: 600; color: {TOKENS['text_0']}; }}
.promise-sub {{ font-size: 0.72rem; color: {TOKENS['text_2']}; font-family: 'JetBrains Mono', monospace; margin-top: 0.15rem; }}
.promise-amount-tag {{
    margin-left: auto;
    background: {TOKENS['accent_soft']}; color: {TOKENS['accent']};
    padding: 0.35rem 0.75rem; border-radius: 10px;
    font-weight: 700; font-size: 0.9rem; font-variant-numeric: tabular-nums;
    letter-spacing: -0.01em;
}}
.chat-body {{
    padding: 1.2rem;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'%3E%3Ccircle cx='20' cy='20' r='0.5' fill='%23ffffff08'/%3E%3C/svg%3E");
    background-color: {TOKENS['bg_2']};
    min-height: 120px;
}}
.chat-bubble {{
    background: linear-gradient(135deg, #005c4b 0%, #007566 100%);
    color: #f0fdfa; padding: 0.75rem 0.95rem;
    border-radius: 12px 12px 12px 4px;
    font-size: 0.92rem; line-height: 1.55;
    max-width: 92%; position: relative;
    box-shadow: 0 4px 15px rgba(0, 92, 75, 0.3), inset 0 1px 0 rgba(255,255,255,0.05);
}}
.chat-time {{
    font-size: 0.68rem; opacity: 0.6; margin-top: 0.35rem;
    text-align: right; font-family: 'JetBrains Mono', monospace;
}}
.promise-footer {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.75rem 1.2rem;
    background: rgba(0, 0, 0, 0.25); border-top: 1px solid {TOKENS['border_soft']};
    font-size: 0.75rem;
}}
.promise-footer .meta-item {{ color: {TOKENS['text_2']}; }}
.promise-footer .meta-item strong {{ color: {TOKENS['text_0']}; font-weight: 600; }}

/* ---------- streamlit overrides ---------- */
/* Tabs — BaseWeb-attribute selectors are the real controls */
[data-baseweb="tab-list"] {{
    background: {TOKENS['bg_1']} !important;
    gap: 0.35rem !important;
    padding: 0.4rem !important;
    border-radius: 14px !important;
    border: 1px solid {TOKENS['border']} !important;
    margin-bottom: 2.5rem !important;
    display: inline-flex !important;
    width: auto !important;
    border-bottom: none !important;
}}
[data-baseweb="tab"] {{
    background: transparent !important;
    color: {TOKENS['text_2']} !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.4rem !important;
    border-radius: 10px !important;
    border: 1px solid transparent !important;
    font-size: 0.9rem !important;
    letter-spacing: -0.005em !important;
    transition: color 180ms, background 180ms, border-color 180ms !important;
    white-space: nowrap !important;
}}
[data-baseweb="tab"] p {{
    color: inherit !important;
    font-weight: inherit !important;
    font-size: inherit !important;
    margin: 0 !important;
    letter-spacing: inherit !important;
}}
[data-baseweb="tab"]:hover {{
    color: {TOKENS['text_1']} !important;
    background: rgba(124, 92, 255, 0.06) !important;
}}
[data-baseweb="tab"][aria-selected="true"] {{
    color: {TOKENS['text_0']} !important;
    background: linear-gradient(135deg, rgba(124, 92, 255, 0.24) 0%, rgba(236, 72, 153, 0.14) 100%) !important;
    border: 1px solid rgba(124, 92, 255, 0.55) !important;
    box-shadow: 0 4px 20px rgba(124, 92, 255, 0.22), inset 0 1px 0 rgba(255,255,255,0.05) !important;
}}
/* Kill Streamlit's default red highlight bar + bottom border */
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{
    display: none !important;
    background-color: transparent !important;
    height: 0 !important;
    width: 0 !important;
}}

/* Hero card wrapper — CSS-based so Streamlit columns nest properly */
.hero-card {{
    background: linear-gradient(135deg, rgba(124, 92, 255, 0.14) 0%, rgba(236, 72, 153, 0.06) 50%, rgba(52, 211, 153, 0.10) 100%),
                {TOKENS['bg_1']};
    border: 1px solid {TOKENS['border']};
    border-radius: 24px;
    padding: 2.25rem 2.25rem 1.75rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}}
.hero-card::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(700px 350px at 100% 0%, {TOKENS['accent_soft']}, transparent 60%);
    pointer-events: none;
    z-index: 0;
}}

[data-testid="stMetric"] {{ background: {TOKENS['bg_1']}; border: 1px solid {TOKENS['border']}; padding: 1rem 1.25rem; border-radius: 12px; }}
[data-testid="stDataFrame"] {{ background: {TOKENS['bg_1']}; border: 1px solid {TOKENS['border']}; border-radius: 12px; padding: 0.25rem; overflow: hidden; }}
[data-testid="stSelectbox"] > div > div, [data-testid="stTextInput"] > div > div, [data-testid="stMultiSelect"] > div > div {{
    background: {TOKENS['bg_1']} !important; border-color: {TOKENS['border']} !important; color: {TOKENS['text_0']} !important;
    border-radius: 10px !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, {TOKENS['accent']} 0%, #ec4899 100%);
    color: white; border: none; border-radius: 10px;
    padding: 0.55rem 1.4rem; font-weight: 600;
    box-shadow: 0 4px 15px rgba(124, 92, 255, 0.3);
    transition: transform 200ms, box-shadow 200ms;
}}
.stButton > button:hover {{ transform: translateY(-1px); box-shadow: 0 6px 20px rgba(124, 92, 255, 0.4); }}

/* ---------- scrollbars ---------- */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {TOKENS['bg_0']}; }}
::-webkit-scrollbar-thumb {{ background: {TOKENS['border']}; border-radius: 5px; }}
::-webkit-scrollbar-thumb:hover {{ background: {TOKENS['accent']}; }}

/* ---------- misc ---------- */
.divider-thin {{ height: 1px; background: {TOKENS['border_soft']}; margin: 1.5rem 0; }}
.kbd {{ padding: 0.15rem 0.55rem; border-radius: 6px; background: {TOKENS['bg_2']}; border: 1px solid {TOKENS['border']}; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: {TOKENS['text_1']}; }}

/* Section header row */
.section-head {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: 2.5rem; margin-bottom: 1rem; }}
.section-head h2 {{ margin: 0 !important; }}
.section-head .caption {{ font-size: 0.85rem; color: {TOKENS['text_2']}; }}
</style>
"""
