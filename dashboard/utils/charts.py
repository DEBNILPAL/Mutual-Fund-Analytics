"""
Bluestock MF Dashboard -- Reusable Chart Builders
=================================================
Plotly-based chart factories with consistent theme.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.theme import CHART_PALETTE, PLOTLY_LAYOUT, PRIMARY, SECONDARY, TIER_COLORS


def _apply_layout(fig: go.Figure, title: str = "", height: int = 420) -> go.Figure:
    """Apply global Plotly layout defaults."""
    fig.update_layout(**PLOTLY_LAYOUT, title=title, height=height)
    return fig


# ── Bar Chart ───────────────────────────────────────────────
def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "",
              orientation: str = "v", color: str | None = None,
              text_col: str | None = None, height: int = 420) -> go.Figure:
    """Vertical or horizontal bar chart."""
    fig = px.bar(
        df, x=x, y=y, orientation=orientation, color=color,
        text=text_col, color_discrete_sequence=CHART_PALETTE,
    )
    fig.update_traces(textposition="outside", textfont_size=10)
    return _apply_layout(fig, title, height)


# ── Line Chart ──────────────────────────────────────────────
def line_chart(df: pd.DataFrame, x: str, y: str | list, title: str = "",
               height: int = 420) -> go.Figure:
    """Single or multi-line chart."""
    if isinstance(y, list):
        fig = go.Figure()
        for i, col in enumerate(y):
            fig.add_trace(go.Scatter(
                x=df[x], y=df[col], mode="lines", name=col,
                line=dict(width=2, color=CHART_PALETTE[i % len(CHART_PALETTE)]),
            ))
    else:
        fig = px.line(df, x=x, y=y, color_discrete_sequence=CHART_PALETTE)
    return _apply_layout(fig, title, height)


# ── Scatter Chart ───────────────────────────────────────────
def scatter_chart(df: pd.DataFrame, x: str, y: str, title: str = "",
                  color: str | None = None, size: str | None = None,
                  hover_name: str | None = None, height: int = 440) -> go.Figure:
    """Scatter with optional color/size encoding."""
    fig = px.scatter(
        df, x=x, y=y, color=color, size=size, hover_name=hover_name,
        color_discrete_sequence=CHART_PALETTE,
    )
    fig.update_traces(marker=dict(line=dict(width=0.5, color="#333")))
    return _apply_layout(fig, title, height)


# ── Donut Chart ─────────────────────────────────────────────
def donut_chart(df: pd.DataFrame, names: str, values: str,
                title: str = "", height: int = 400) -> go.Figure:
    """Donut / pie chart."""
    fig = px.pie(
        df, names=names, values=values, hole=0.45,
        color_discrete_sequence=CHART_PALETTE,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label",
                      textfont_size=10)
    return _apply_layout(fig, title, height)


# ── Heatmap ─────────────────────────────────────────────────
def heatmap_chart(z: np.ndarray, x_labels: list, y_labels: list,
                  title: str = "", height: int = 500,
                  colorscale: str = "RdYlGn",
                  fmt: str = ".1f") -> go.Figure:
    """Annotated heatmap."""
    annotations = []
    for i, row in enumerate(z):
        for j, val in enumerate(row):
            if not np.isnan(val):
                annotations.append(dict(
                    x=x_labels[j], y=y_labels[i],
                    text=f"{val:{fmt}}", showarrow=False,
                    font=dict(size=10, color="white" if abs(val) > 15 else "black"),
                ))
    fig = go.Figure(data=go.Heatmap(
        z=z, x=x_labels, y=y_labels, colorscale=colorscale,
        hoverongaps=False, colorbar=dict(title="Value"),
    ))
    fig.update_layout(annotations=annotations)
    return _apply_layout(fig, title, height)


# ── Radar Chart ─────────────────────────────────────────────
def radar_chart(categories: list, values_dict: dict[str, list],
                title: str = "", height: int = 480) -> go.Figure:
    """Multi-trace radar / spider chart."""
    fig = go.Figure()
    cats_closed = categories + [categories[0]]
    for i, (name, vals) in enumerate(values_dict.items()):
        vals_closed = vals + [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals_closed, theta=cats_closed, fill="toself",
            name=name[:35], opacity=0.7,
            line=dict(color=CHART_PALETTE[i % len(CHART_PALETTE)]),
        ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
    return _apply_layout(fig, title, height)


# ── Horizontal Ranking Bar ──────────────────────────────────
def ranking_bar(df: pd.DataFrame, name_col: str, value_col: str,
                title: str = "", n: int = 10, height: int = 420,
                fmt: str = ".2f", ascending: bool = False) -> go.Figure:
    """Top-N horizontal bar chart for rankings."""
    sorted_df = df.nlargest(n, value_col) if not ascending else df.nsmallest(n, value_col)
    sorted_df = sorted_df.sort_values(value_col, ascending=True)
    labels = sorted_df[name_col].str[:35]
    values = sorted_df[value_col]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=CHART_PALETTE[:n][::-1]),
        text=[f"{v:{fmt}}" for v in values],
        textposition="outside", textfont_size=10,
    ))
    return _apply_layout(fig, title, height)


# ── Growth of Rs.100 ────────────────────────────────────────
def growth_chart(series_dict: dict[str, pd.DataFrame],
                 date_col: str, value_col: str,
                 title: str = "Growth of Rs.100",
                 dash_keys: list | None = None,
                 height: int = 460) -> go.Figure:
    """Line chart showing normalised growth of Rs.100."""
    fig = go.Figure()
    for i, (name, df) in enumerate(series_dict.items()):
        df = df.sort_values(date_col)
        if len(df) == 0:
            continue
        growth = (df[value_col] / df[value_col].iloc[0]) * 100
        dash = "dash" if dash_keys and name in dash_keys else "solid"
        fig.add_trace(go.Scatter(
            x=df[date_col], y=growth, mode="lines",
            name=name[:40],
            line=dict(width=2.5 if dash == "dash" else 2, dash=dash,
                      color=CHART_PALETTE[i % len(CHART_PALETTE)]),
        ))
    fig.add_hline(y=100, line_dash="dot", line_color="#999",
                  annotation_text="Rs.100")
    return _apply_layout(fig, title, height)


# ── Box Plot ────────────────────────────────────────────────
def box_chart(df: pd.DataFrame, x: str, y: str,
              title: str = "", height: int = 420) -> go.Figure:
    """Box plot by category."""
    fig = px.box(df, x=x, y=y, color=x,
                 color_discrete_sequence=CHART_PALETTE)
    fig.update_layout(showlegend=False)
    return _apply_layout(fig, title, height)
