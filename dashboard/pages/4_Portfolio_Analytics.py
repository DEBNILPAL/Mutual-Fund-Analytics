"""
Page 4 -- Portfolio & Benchmark Analytics
==========================================
Sector Allocation | Top Holdings | Benchmark Comparison |
Growth of Rs.100 | Rolling Correlation | Tracking Error |
Diversification Score | Sector Concentration | Risk Table
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.theme import (
    CUSTOM_CSS, PRIMARY, SECONDARY, CHART_PALETTE,
    kpi_card_html, status_bar_html, insight_html,
)
from utils.database import (
    db_status, get_portfolio_data, get_benchmark_data,
    get_nav_data, get_fund_master, get_scorecard, get_tracking_error,
)
from utils.charts import (
    donut_chart, ranking_bar, growth_chart, scatter_chart, line_chart,
    bar_chart, heatmap_chart,
)
from utils.insights import portfolio_insights

st.set_page_config(page_title="Portfolio Analytics | Bluestock MF", page_icon=":material/trending_up:", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────
st.markdown(f'<h1 style="color:{PRIMARY};">Portfolio & Benchmark Analytics</h1>', unsafe_allow_html=True)

info = db_status()
st.markdown(status_bar_html(info["status"], info["last_refresh"], info["total_rows"]), unsafe_allow_html=True)

# ── Load Data ───────────────────────────────────────────────
portfolio = get_portfolio_data()
benchmark = get_benchmark_data()
nav_data = get_nav_data()
fund_master = get_fund_master()
scorecard = get_scorecard()
te_df = get_tracking_error()

# ── Filters ─────────────────────────────────────────────────
with st.expander("Filters", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        funds_in_portfolio = portfolio["amfi_code"].unique()
        fund_names = fund_master[fund_master["amfi_code"].isin(funds_in_portfolio)]["scheme_name"].tolist()
        sel_fund = st.multiselect("Fund", fund_names, key="pa_fund")
    with fc2:
        bench_indices = sorted(benchmark["index_name"].unique().tolist())
        sel_bench = st.multiselect("Benchmark", bench_indices,
                                   default=["NIFTY50", "NIFTY100"], key="pa_bench")
    with fc3:
        sectors = sorted(portfolio["sector"].unique().tolist())
        sel_sector = st.multiselect("Sector", sectors, key="pa_sector")

# Apply filters
port_view = portfolio.copy()
if sel_fund:
    codes = fund_master[fund_master["scheme_name"].isin(sel_fund)]["amfi_code"].tolist()
    port_view = port_view[port_view["amfi_code"].isin(codes)]
if sel_sector:
    port_view = port_view[port_view["sector"].isin(sel_sector)]

# ── KPI Cards ───────────────────────────────────────────────
n_holdings = port_view["stock_name"].nunique()
n_sectors = port_view["sector"].nunique()
n_funds_port = port_view["amfi_code"].nunique()
total_mkt_val = port_view["market_value_cr"].sum()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi_card_html("Unique Holdings", f"{n_holdings}"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card_html("Sectors Covered", f"{n_sectors}"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card_html("Funds with Holdings", f"{n_funds_port}"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card_html("Total Market Value", f"Rs.{total_mkt_val:,.0f} Cr"), unsafe_allow_html=True)

st.markdown("")

# ── Insights ────────────────────────────────────────────────
insights = portfolio_insights(port_view)
if insights:
    with st.expander("Key Insights", expanded=True):
        for ins in insights:
            st.markdown(insight_html(ins), unsafe_allow_html=True)

# ── Charts ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Portfolio Holdings", "Benchmark Analysis", "Risk Analysis"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        # Sector Allocation Donut
        sector_alloc = port_view.groupby("sector")["weight_pct"].sum().reset_index()
        sector_alloc.columns = ["Sector", "Total Weight (%)"]
        sector_alloc = sector_alloc.sort_values("Total Weight (%)", ascending=False)
        fig = donut_chart(sector_alloc, "Sector", "Total Weight (%)",
                          title="Sector Allocation (Aggregate)")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Top Holdings
        top_holdings = port_view.groupby("stock_name").agg(
            total_weight=("weight_pct", "sum"),
            sector=("sector", "first"),
            funds_count=("amfi_code", "nunique"),
        ).reset_index().sort_values("total_weight", ascending=False).head(15)
        fig = ranking_bar(top_holdings, "stock_name", "total_weight",
                          title="Top 15 Holdings by Weight", n=15, fmt=".1f",
                          height=480)
        st.plotly_chart(fig, use_container_width=True)

    # Sector Concentration Analysis
    st.markdown(f'<div class="section-header">Sector Concentration Analysis</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        fig = bar_chart(sector_alloc.head(10), "Sector", "Total Weight (%)",
                        title="Top 10 Sectors by Aggregate Weight")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        # Diversification Score (HHI-based)
        fund_divs = []
        for code in port_view["amfi_code"].unique():
            fund_port = port_view[port_view["amfi_code"] == code]
            weights = fund_port["weight_pct"].values / fund_port["weight_pct"].sum()
            hhi = np.sum(weights ** 2)
            div_score = (1 - hhi) * 100
            name = fund_master[fund_master["amfi_code"] == code]["scheme_name"].values
            fund_divs.append({
                "Fund": name[0][:35] if len(name) else str(code),
                "Diversification Score": round(div_score, 1),
            })
        div_df = pd.DataFrame(fund_divs).sort_values("Diversification Score", ascending=False)
        fig = ranking_bar(div_df, "Fund", "Diversification Score",
                          title="Portfolio Diversification Score (100 = Most Diversified)",
                          n=len(div_df), fmt=".1f", height=420)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    # Benchmark Comparison -- Growth of Rs.100
    st.markdown(f'<div class="section-header">Benchmark Comparison</div>', unsafe_allow_html=True)

    # Fund selector for benchmark comparison
    top5_codes = scorecard.sort_values("composite_score", ascending=False).head(5)["amfi_code"].tolist()
    top5_names = fund_master[fund_master["amfi_code"].isin(top5_codes)].set_index("amfi_code")["scheme_name"].to_dict()

    series_dict = {}
    for code in top5_codes:
        name = top5_names.get(code, str(code))
        fund_nav = nav_data[nav_data["amfi_code"] == code].sort_values("date")
        if not fund_nav.empty:
            # Use last 3 years
            cutoff = fund_nav["date"].max() - pd.DateOffset(years=3)
            fund_nav = fund_nav[fund_nav["date"] >= cutoff].copy()
            fund_nav = fund_nav.rename(columns={"nav": "value"})
            series_dict[name[:35]] = fund_nav

    bench_to_show = sel_bench if sel_bench else ["NIFTY50", "NIFTY100"]
    dash_keys = []
    for idx_name in bench_to_show:
        bsub = benchmark[benchmark["index_name"] == idx_name].sort_values("date")
        if not bsub.empty:
            cutoff = bsub["date"].max() - pd.DateOffset(years=3)
            bsub = bsub[bsub["date"] >= cutoff].copy()
            bsub = bsub.rename(columns={"close_value": "value"})
            series_dict[idx_name] = bsub
            dash_keys.append(idx_name)

    if series_dict:
        fig = growth_chart(series_dict, "date", "value",
                           title="Growth of Rs.100 -- Top 5 Funds vs Benchmarks (3Y)",
                           dash_keys=dash_keys, height=500)
        st.plotly_chart(fig, use_container_width=True)

    # Rolling Correlation
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="section-header">Rolling Correlation with Nifty 100</div>',
                    unsafe_allow_html=True)
        bench_n100 = benchmark[benchmark["index_name"] == "NIFTY100"].sort_values("date")
        if not bench_n100.empty:
            bench_n100["bench_return"] = bench_n100["close_value"].pct_change()
            fig_rc = go.Figure()
            for i, code in enumerate(top5_codes[:3]):
                fund_nav = nav_data[nav_data["amfi_code"] == code].sort_values("date")
                fund_nav["fund_return"] = fund_nav["nav"].pct_change()
                merged = fund_nav[["date", "fund_return"]].merge(
                    bench_n100[["date", "bench_return"]], on="date"
                ).dropna()
                merged["rolling_corr"] = merged["fund_return"].rolling(252).corr(merged["bench_return"])
                name = top5_names.get(code, str(code))[:30]
                fig_rc.add_trace(go.Scatter(
                    x=merged["date"], y=merged["rolling_corr"],
                    mode="lines", name=name,
                    line=dict(width=2, color=CHART_PALETTE[i]),
                ))
            fig_rc.add_hline(y=0, line_dash="dash", line_color="#999")
            fig_rc.update_layout(
                title="Rolling 1-Year Correlation with Nifty 100",
                height=420, yaxis_title="Correlation",
                xaxis_title="Date",
            )
            st.plotly_chart(fig_rc, use_container_width=True)

    with c2:
        # Tracking Error by Fund
        st.markdown(f'<div class="section-header">Tracking Error by Fund</div>',
                    unsafe_allow_html=True)
        if not te_df.empty:
            te_plot = te_df.copy()
            te_plot["te_pct"] = te_plot["tracking_error"] * 100
            fig = ranking_bar(te_plot, "scheme_name", "te_pct",
                              title="Tracking Error (% Annualised)",
                              n=15, fmt=".1f", ascending=True)
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    # Top Holdings Risk Table
    st.markdown(f'<div class="section-header">Top Holdings Risk Assessment</div>',
                unsafe_allow_html=True)

    risk_table = port_view.copy()
    fund_name_map = fund_master.set_index("amfi_code")["scheme_name"].to_dict()
    risk_table["Fund"] = risk_table["amfi_code"].map(fund_name_map).fillna("Unknown")

    def concentration_risk(weight: float) -> str:
        if weight > 10:
            return "High"
        elif weight >= 5:
            return "Moderate"
        else:
            return "Low"

    risk_table["Concentration Risk"] = risk_table["weight_pct"].apply(concentration_risk)
    risk_display = risk_table[["Fund", "sector", "stock_name", "weight_pct", "Concentration Risk"]].copy()
    risk_display.columns = ["Fund", "Sector", "Holding", "Weight %", "Risk Level"]
    risk_display = risk_display.sort_values("Weight %", ascending=False).head(30)

    def highlight_risk(val):
        if val == "High":
            return "background-color: #FEE2E2; color: #991B1B"
        elif val == "Moderate":
            return "background-color: #FEF3C7; color: #92400E"
        else:
            return "background-color: #D1FAE5; color: #065F46"

    styled = risk_display.style.applymap(
        highlight_risk, subset=["Risk Level"]
    ).format({"Weight %": "{:.2f}"})
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

    # Concentration summary
    c1, c2 = st.columns(2)
    with c1:
        risk_counts = risk_table["Concentration Risk"].value_counts().reset_index()
        risk_counts.columns = ["Risk Level", "Count"]
        fig = donut_chart(risk_counts, "Risk Level", "Count",
                          title="Holdings by Concentration Risk")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Sector-wise average weight
        sector_avg = port_view.groupby("sector")["weight_pct"].mean().reset_index()
        sector_avg.columns = ["Sector", "Avg Weight (%)"]
        sector_avg = sector_avg.sort_values("Avg Weight (%)", ascending=False)
        fig = bar_chart(sector_avg, "Sector", "Avg Weight (%)",
                        title="Average Holding Weight by Sector")
        fig.update_layout(xaxis_tickangle=30)
        st.plotly_chart(fig, use_container_width=True)

# ── Export ──────────────────────────────────────────────────
with st.expander("Download Data"):
    st.download_button("Download Portfolio (CSV)", portfolio.to_csv(index=False),
                       "portfolio_holdings.csv", "text/csv")
    st.download_button("Download Tracking Error (CSV)", te_df.to_csv(index=False),
                       "tracking_error.csv", "text/csv")
