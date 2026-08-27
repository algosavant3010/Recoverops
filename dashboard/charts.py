"""Plotly chart builders. Dark palette, tight annotations, no chart-junk."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from theme import TOKENS


def _base_layout(height: int = 340) -> dict[str, Any]:
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TOKENS["text_1"], size=13),
        margin=dict(l=40, r=20, t=40, b=40),
        height=height,
        hoverlabel=dict(bgcolor=TOKENS["bg_2"], font=dict(color=TOKENS["text_0"]), bordercolor=TOKENS["accent"]),
        xaxis=dict(gridcolor=TOKENS["border_soft"], zerolinecolor=TOKENS["border"], color=TOKENS["text_2"]),
        yaxis=dict(gridcolor=TOKENS["border_soft"], zerolinecolor=TOKENS["border"], color=TOKENS["text_2"]),
    )


def strategy_comparison_chart(strategies: list[dict]) -> go.Figure:
    """Grouped bars: money recovered vs money at risk per strategy."""
    names = [s["name"] for s in strategies]
    recovered = [s["total_recovered_paise"] / 100 for s in strategies]
    at_risk = [s["total_at_risk_paise"] / 100 for s in strategies]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="At risk",
            x=names,
            y=at_risk,
            marker=dict(color=TOKENS["border"], line=dict(color=TOKENS["border"])),
            hovertemplate="₹%{y:,.0f}<extra>At risk</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Recovered",
            x=names,
            y=recovered,
            marker=dict(color=TOKENS["accent"]),
            text=[f"₹{v:,.0f}" for v in recovered],
            textposition="outside",
            textfont=dict(color=TOKENS["text_0"], size=13, family="Inter"),
            hovertemplate="₹%{y:,.0f}<extra>Recovered</extra>",
        )
    )
    layout = _base_layout(height=380)
    layout.update(
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(**layout["yaxis"], tickformat=",.0s", title="Rupees"),
    )
    fig.update_layout(**layout)
    return fig


def recovery_rate_bullet(strategies: list[dict]) -> go.Figure:
    """Horizontal bullet-style bar of recovery rate per strategy."""
    names = [s["name"] for s in strategies][::-1]
    rates = [s["recovery_rate"] * 100 for s in strategies][::-1]
    colors = [TOKENS["accent"] if n == "recoverops" else TOKENS["text_2"] for n in names]

    fig = go.Figure(
        go.Bar(
            x=rates,
            y=names,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{r:.1f}%" for r in rates],
            textposition="outside",
            textfont=dict(color=TOKENS["text_0"], size=13, family="Inter"),
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )
    )
    layout = _base_layout(height=220)
    layout.update(
        xaxis=dict(**layout["xaxis"], range=[0, max(rates) * 1.25 or 10], ticksuffix="%"),
        yaxis=dict(**layout["yaxis"], categoryorder="array", categoryarray=names),
        margin=dict(l=100, r=40, t=20, b=30),
    )
    fig.update_layout(**layout)
    return fig


def confusion_heatmap(matrix: dict[str, dict[str, int]]) -> go.Figure:
    """Diagonal-emphasized heatmap of true vs predicted causes."""
    labels = sorted(set(matrix.keys()) | {p for row in matrix.values() for p in row.keys()})
    z = [[matrix.get(t, {}).get(p, 0) for p in labels] for t in labels]
    text = [[str(v) if v else "" for v in row] for row in z]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=labels,
            y=labels,
            colorscale=[[0.0, TOKENS["bg_1"]], [0.5, "#5940bf"], [1.0, TOKENS["accent"]]],
            showscale=False,
            text=text,
            texttemplate="%{text}",
            textfont=dict(color=TOKENS["text_0"], size=13, family="JetBrains Mono"),
            hovertemplate="True: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>",
        )
    )
    layout = _base_layout(height=460)
    layout.update(
        xaxis=dict(**layout["xaxis"], side="top", title="Predicted"),
        yaxis=dict(**layout["yaxis"], autorange="reversed", title="True"),
        margin=dict(l=120, r=20, t=60, b=20),
    )
    fig.update_layout(**layout)
    return fig


def exceptions_donut(exceptions: list[dict]) -> go.Figure:
    """Donut of unrecovered amount by reason."""
    from collections import defaultdict

    by_reason: dict[str, int] = defaultdict(int)
    for e in exceptions:
        by_reason[e["reason"]] += e["amount_paise"]
    labels = list(by_reason.keys())
    values = [v / 100 for v in by_reason.values()]

    palette = [TOKENS["danger"], TOKENS["warn"], TOKENS["info"], TOKENS["text_2"], TOKENS["success"]]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.68,
            marker=dict(colors=palette[: len(labels)], line=dict(color=TOKENS["bg_0"], width=2)),
            textinfo="label+percent",
            textfont=dict(color=TOKENS["text_0"], family="Inter", size=12),
            hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>",
        )
    )
    total = sum(values)
    layout = _base_layout(height=380)
    layout.update(
        annotations=[
            dict(text=f"₹{total:,.0f}<br><span style='font-size:0.7rem;color:{TOKENS['text_2']}'>unrecovered</span>",
                 x=0.5, y=0.5, font=dict(color=TOKENS["text_0"], size=18, family="Inter"), showarrow=False),
        ],
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_layout(**layout)
    return fig


def per_cause_metrics_chart(per_cause: dict[str, dict]) -> go.Figure:
    """Grouped bar chart of precision/recall/F1 per cause."""
    causes = sorted(per_cause.keys(), key=lambda c: per_cause[c]["support"], reverse=True)
    precisions = [per_cause[c]["precision"] * 100 for c in causes]
    recalls = [per_cause[c]["recall"] * 100 for c in causes]
    f1s = [per_cause[c]["f1"] * 100 for c in causes]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Precision", x=causes, y=precisions, marker_color=TOKENS["accent"]))
    fig.add_trace(go.Bar(name="Recall", x=causes, y=recalls, marker_color=TOKENS["success"]))
    fig.add_trace(go.Bar(name="F1", x=causes, y=f1s, marker_color=TOKENS["info"]))

    layout = _base_layout(height=380)
    layout.update(
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(**layout["yaxis"], ticksuffix="%", range=[0, 110]),
    )
    fig.update_layout(**layout)
    return fig
