"""
Page 1 -- Indian Mutual Fund Industry Overview
===============================================
KPI Cards | AUM Growth | SIP Trend | Folio Growth |
Category Inflow Heatmap | Top 10 AMCs
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st

from config.theme import (
    CUSTOM_CSS, PRIMARY, SECONDARY, kpi_card_html,
    status_bar_html, insight_html,
)
from utils.database import (
    db_status, get_aum_data, get_sip_data, get_industry_folios,
    get_category_inflows, get_fund_master,
)
from utils.charts import line_chart, bar_chart, heatmap_chart, ranking_bar
from utils.insights import market_insights

st.set_page_config(page_title="Market Overview | Bluestock MF", page_icon=":material/trending_up:", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────
st.markdown(f'<h1 style="color:{PRIMARY};">Indian Mutual Fund Industry Overview</h1>', unsafe_allow_html=True)

info = db_status()
st.markdown(status_bar_html(info["status"], info["last_refresh"], info["total_rows"]), unsafe_allow_html=True)

# ── Load Data ───────────────────────────────────────────────
aum_df = get_aum_data()
sip_df = get_sip_data()
folio_df = get_industry_folios()
cat_inflows = get_category_inflows()
fund_master = get_fund_master()

# ── Filters ─────────────────────────────────────────────────
with st.expander("Filters", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        years = sorted(aum_df["date"].dt.year.unique().tolist())
        sel_year = st.selectbox("Year", ["All"] + years, key="mo_year")
    with fc2:
        amcs = sorted(aum_df["fund_house"].unique().tolist())
        sel_amc = st.multiselect("AMC", amcs, key="mo_amc")
    with fc3:
        categories = sorted(cat_inflows["category"].unique().tolist())
        sel_cat = st.multiselect("Category", categories, key="mo_cat")

# Apply filters
aum_view = aum_df.copy()
if sel_year != "All":
    aum_view = aum_view[aum_view["date"].dt.year == sel_year]
if sel_amc:
    aum_view = aum_view[aum_view["fund_house"].isin(sel_amc)]

cat_view = cat_inflows.copy()
if sel_cat:
    cat_view = cat_view[cat_view["category"].isin(sel_cat)]

# ── KPI Cards ───────────────────────────────────────────────
latest_aum = aum_df[aum_df["date"] == aum_df["date"].max()]
total_aum = latest_aum["aum_lakh_crore"].sum()
total_schemes = int(latest_aum["num_schemes"].sum())

latest_sip = sip_df.sort_values("date").iloc[-1] if not sip_df.empty else None
latest_folio = folio_df.sort_values("date").iloc[-1] if not folio_df.empty else None

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(kpi_card_html("Industry AUM", f"Rs.{total_aum:.1f}L Cr"), unsafe_allow_html=True)
with k2:
    val = f"{latest_folio['total_folios_crore']:.2f} Cr" if latest_folio is not None else "N/A"
    st.markdown(kpi_card_html("Total Folios", val), unsafe_allow_html=True)
with k3:
    val = f"Rs.{latest_sip['sip_inflow_crore']:,.0f} Cr" if latest_sip is not None else "N/A"
    st.markdown(kpi_card_html("Monthly SIP Inflow", val), unsafe_allow_html=True)
with k4:
    val = f"{latest_sip['active_sip_accounts_crore']:.2f} Cr" if latest_sip is not None else "N/A"
    st.markdown(kpi_card_html("Active SIP Accounts", val), unsafe_allow_html=True)
with k5:
    st.markdown(kpi_card_html("Total Schemes", f"{total_schemes:,}"), unsafe_allow_html=True)

st.markdown("")

# ── Dynamic Insights ────────────────────────────────────────
insights = market_insights(aum_df, sip_df, folio_df)
if insights:
    with st.expander("Key Insights", expanded=True):
        for ins in insights:
            st.markdown(insight_html(ins), unsafe_allow_html=True)

# ── Charts ──────────────────────────────────────────────────
st.markdown(f'<div class="section-header">Industry AUM Growth</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    # AUM Growth by AMC over time
    aum_total = aum_view.groupby("date")["aum_lakh_crore"].sum().reset_index()
    fig = line_chart(aum_total, "date", "aum_lakh_crore",
                     title="Total Industry AUM (Lakh Crore)")
    fig.update_yaxes(title_text="AUM (Lakh Crore)")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # SIP Inflow Trend
    fig = line_chart(sip_df, "date", "sip_inflow_crore",
                     title="Monthly SIP Inflows (Crore)")
    fig.update_yaxes(title_text="SIP Inflow (Crore)")
    # Highlight Rs.31,002 Cr milestone
    if not sip_df.empty:
        max_sip = sip_df["sip_inflow_crore"].max()
        fig.add_hline(y=max_sip, line_dash="dot", line_color=SECONDARY,
                      annotation_text=f"Rs.{max_sip:,.0f} Cr Milestone")
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f'<div class="section-header">Folio & Category Analysis</div>', unsafe_allow_html=True)

c3, c4 = st.columns(2)

with c3:
    # Folio Growth
    if not folio_df.empty:
        fig = line_chart(folio_df, "date", "total_folios_crore",
                         title="Industry Folio Count (Crore)")
        fig.update_yaxes(title_text="Folios (Crore)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Folio data not available.")

with c4:
    # Category Inflow Heatmap
    if not cat_view.empty:
        pivot = cat_view.pivot_table(
            index="category", columns=cat_view["date"].dt.strftime("%Y-%m"),
            values="net_inflow_crore", aggfunc="sum"
        ).fillna(0)
        fig = heatmap_chart(
            z=pivot.values, x_labels=pivot.columns.tolist(),
            y_labels=pivot.index.tolist(),
            title="Category Net Inflows Heatmap (Crore)",
            height=460, fmt=".0f",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Category inflow data not available.")

# Top 10 AMCs by AUM
st.markdown(f'<div class="section-header">Top AMCs by AUM</div>', unsafe_allow_html=True)

top_amcs = latest_aum.nlargest(10, "aum_lakh_crore").copy()
top_amcs["aum_label"] = top_amcs["aum_lakh_crore"].apply(lambda x: f"Rs.{x:.1f}L Cr")
fig = ranking_bar(
    top_amcs, "fund_house", "aum_lakh_crore",
    title="Top 10 AMCs by AUM (Lakh Crore)", n=10, fmt=".1f",
)
st.plotly_chart(fig, use_container_width=True)

# ── Export ──────────────────────────────────────────────────
with st.expander("Download Data"):
    st.download_button(
        "Download AUM Data (CSV)", aum_df.to_csv(index=False),
        "aum_data.csv", "text/csv",
    )
    st.download_button(
        "Download SIP Data (CSV)", sip_df.to_csv(index=False),
        "sip_data.csv", "text/csv",
    )
