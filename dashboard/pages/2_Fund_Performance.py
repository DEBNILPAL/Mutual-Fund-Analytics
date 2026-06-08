"""
Page 2 -- Fund Performance & Risk Analytics
============================================
KPI Cards | Sharpe | Sortino | Alpha-Beta | Risk-Return |
Scorecard | Drawdown | Tracking Error | CAGR Heatmap |
Fund Comparison Tool | Benchmark Quick Comparison
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st

from config.theme import (
    CUSTOM_CSS, PRIMARY, SECONDARY, CHART_PALETTE,
    kpi_card_html, status_bar_html, insight_html,
)
from utils.database import (
    db_status, get_fund_master, get_scorecard, get_sharpe, get_sortino,
    get_alpha_beta, get_cagr, get_max_drawdown, get_tracking_error,
    get_benchmark_data, get_nav_data,
)
from utils.charts import (
    ranking_bar, scatter_chart, heatmap_chart, radar_chart, line_chart,
    bar_chart, box_chart, growth_chart,
)
from utils.insights import performance_insights

st.set_page_config(page_title="Fund Performance | Bluestock MF", page_icon=":material/trending_up:", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────
st.markdown(f'<h1 style="color:{PRIMARY};">Fund Performance & Risk Analytics</h1>', unsafe_allow_html=True)

info = db_status()
st.markdown(status_bar_html(info["status"], info["last_refresh"], info["total_rows"]), unsafe_allow_html=True)

# ── Load Data ───────────────────────────────────────────────
fund_master = get_fund_master()
scorecard = get_scorecard()
sharpe_df = get_sharpe()
sortino_df = get_sortino()
ab_df = get_alpha_beta()
cagr_df = get_cagr()
dd_df = get_max_drawdown()
te_df = get_tracking_error()

# ── Filters ─────────────────────────────────────────────────
with st.expander("Filters", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        amcs = sorted(fund_master["fund_house"].unique().tolist())
        sel_amc = st.multiselect("AMC", amcs, key="fp_amc")
    with fc2:
        cats = sorted(fund_master["category"].unique().tolist())
        sel_cat = st.multiselect("Category", cats, key="fp_cat")
    with fc3:
        risk_cats = sorted(fund_master["risk_category"].dropna().unique().tolist())
        sel_risk = st.multiselect("Risk Category", risk_cats, key="fp_risk")

# Apply filters
if sel_amc or sel_cat or sel_risk:
    mask = pd.Series(True, index=fund_master.index)
    if sel_amc:
        mask &= fund_master["fund_house"].isin(sel_amc)
    if sel_cat:
        mask &= fund_master["category"].isin(sel_cat)
    if sel_risk:
        mask &= fund_master["risk_category"].isin(sel_risk)
    active_codes = fund_master[mask]["amfi_code"].tolist()
    scorecard = scorecard[scorecard["amfi_code"].isin(active_codes)]
    sharpe_df = sharpe_df[sharpe_df["amfi_code"].isin(active_codes)]
    sortino_df = sortino_df[sortino_df["amfi_code"].isin(active_codes)]
    ab_df = ab_df[ab_df["amfi_code"].isin(active_codes)]
    cagr_df = cagr_df[cagr_df["amfi_code"].isin(active_codes)]
    dd_df = dd_df[dd_df["amfi_code"].isin(active_codes)]
    te_df = te_df[te_df["amfi_code"].isin(active_codes)]

# ── KPI Cards ───────────────────────────────────────────────
best_sharpe = sharpe_df.sort_values("sharpe_ratio", ascending=False).iloc[0] if not sharpe_df.empty else None
best_cagr = cagr_df.sort_values("cagr_3yr", ascending=False).iloc[0] if not cagr_df.empty else None
lowest_dd = dd_df.sort_values("max_drawdown_pct", ascending=False).iloc[0] if not dd_df.empty else None
best_alpha = ab_df.sort_values("alpha_annual", ascending=False).iloc[0] if not ab_df.empty else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    val = f"{best_sharpe['sharpe_ratio']:.2f}" if best_sharpe is not None else "N/A"
    st.markdown(kpi_card_html("Best Sharpe", val), unsafe_allow_html=True)
with k2:
    val = f"{best_cagr['cagr_3yr']*100:.1f}%" if best_cagr is not None else "N/A"
    st.markdown(kpi_card_html("Best 3Y CAGR", val), unsafe_allow_html=True)
with k3:
    val = f"{lowest_dd['max_drawdown_pct']:.1f}%" if lowest_dd is not None else "N/A"
    st.markdown(kpi_card_html("Lowest Drawdown", val), unsafe_allow_html=True)
with k4:
    val = f"{best_alpha['alpha_annual']*100:.1f}%" if best_alpha is not None else "N/A"
    st.markdown(kpi_card_html("Highest Alpha", val), unsafe_allow_html=True)

st.markdown("")

# ── Insights ────────────────────────────────────────────────
insights = performance_insights(scorecard, sharpe_df, cagr_df, dd_df)
if insights:
    with st.expander("Key Insights", expanded=True):
        for ins in insights:
            st.markdown(insight_html(ins), unsafe_allow_html=True)

# ── Charts ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Risk-Adjusted Rankings", "Alpha & Beta", "Drawdown & TE", "CAGR Analysis"
])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        # Sharpe Ranking
        fig = ranking_bar(sharpe_df, "scheme_name", "sharpe_ratio",
                          title="Sharpe Ratio Ranking (Rf = 6.5%)", n=10)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        # Sortino Ranking
        fig = ranking_bar(sortino_df, "scheme_name", "sortino_ratio",
                          title="Sortino Ratio Ranking", n=10)
        st.plotly_chart(fig, use_container_width=True)

    # Scorecard Ranking
    st.markdown(f'<div class="section-header">Composite Fund Scorecard</div>', unsafe_allow_html=True)
    sc_sorted = scorecard.sort_values("composite_score", ascending=False).head(20)
    fig = ranking_bar(sc_sorted, "scheme_name", "composite_score",
                      title="Top 20 Funds -- Composite Score", n=20, fmt=".1f",
                      height=520)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        # Alpha vs Beta scatter
        ab_plot = ab_df.copy()
        ab_plot["alpha_pct"] = ab_plot["alpha_annual"] * 100
        ab_plot["label"] = ab_plot["scheme_name"].str[:30]
        fig = scatter_chart(
            ab_plot, "beta", "alpha_pct",
            title="Alpha vs Beta (Benchmark: Nifty 100)",
            hover_name="label",
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#999")
        fig.add_vline(x=1.0, line_dash="dash", line_color="#999")
        fig.update_xaxes(title_text="Beta")
        fig.update_yaxes(title_text="Annualised Alpha (%)")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Risk vs Return Scatter
        risk_return = cagr_df[["amfi_code", "cagr_3yr"]].merge(
            fund_master[["amfi_code", "category"]], on="amfi_code"
        )
        risk_return["cagr_pct"] = risk_return["cagr_3yr"] * 100
        fig = scatter_chart(
            risk_return, "amfi_code", "cagr_pct",
            title="3-Year CAGR by Fund",
            color="category",
        )
        fig.update_xaxes(title_text="Fund (AMFI Code)")
        fig.update_yaxes(title_text="3Y CAGR (%)")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        # Drawdown Analysis
        fig = ranking_bar(
            dd_df, "scheme_name", "max_drawdown_pct",
            title="Worst Maximum Drawdowns", n=10, ascending=True, fmt=".1f",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Tracking Error Distribution
        import plotly.express as px
        fig = px.histogram(
            te_df, x="tracking_error", nbins=15,
            title="Tracking Error Distribution",
            color_discrete_sequence=[PRIMARY],
        )
        fig.update_layout(height=420, xaxis_title="Tracking Error",
                          yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    # CAGR Heatmap
    cagr_merged = cagr_df.copy()
    if "scheme_name" not in cagr_merged.columns:
        cagr_merged = cagr_merged.merge(
            fund_master[["amfi_code", "scheme_name"]], on="amfi_code"
        )
    cagr_sorted = cagr_merged.sort_values("cagr_3yr", ascending=False).head(20)
    labels_y = cagr_sorted["scheme_name"].str[:30].tolist()
    z_data = cagr_sorted[["cagr_1yr", "cagr_3yr", "cagr_5yr"]].values * 100
    fig = heatmap_chart(
        z=z_data, x_labels=["1Y CAGR", "3Y CAGR", "5Y CAGR"],
        y_labels=labels_y,
        title="CAGR Comparison Heatmap -- Top 20 Funds",
        height=580,
    )
    st.plotly_chart(fig, use_container_width=True)

# ═════════════════════════════════════════════════════════════
# FUND COMPARISON TOOL
# ═════════════════════════════════════════════════════════════
st.markdown(f'<div class="section-header">Fund Comparison Tool</div>', unsafe_allow_html=True)

all_funds = scorecard["scheme_name"].tolist() if not scorecard.empty else []
comp_c1, comp_c2, comp_c3 = st.columns(3)
with comp_c1:
    fund_a = st.selectbox("Fund A", all_funds, index=0 if all_funds else 0, key="fund_a")
with comp_c2:
    fund_b = st.selectbox("Fund B", all_funds,
                          index=min(1, len(all_funds)-1) if len(all_funds) > 1 else 0,
                          key="fund_b")
with comp_c3:
    bench_sel = st.selectbox("Benchmark", ["NIFTY50", "NIFTY100", "NIFTY_MIDCAP150"],
                             index=1, key="bench_comp")

if fund_a and fund_b and fund_a != fund_b:
    # Build comparison table
    metrics_to_compare = []
    for fund_name in [fund_a, fund_b]:
        row = {}
        row["Fund"] = fund_name

        sc_row = scorecard[scorecard["scheme_name"] == fund_name]
        cagr_row = cagr_df[cagr_df["scheme_name"] == fund_name] if "scheme_name" in cagr_df.columns else cagr_df.merge(
            fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
        ).pipe(lambda d: d[d["scheme_name"] == fund_name])
        sharpe_row = sharpe_df[sharpe_df["scheme_name"] == fund_name]
        sortino_row = sortino_df[sortino_df["scheme_name"] == fund_name]
        ab_row = ab_df[ab_df["scheme_name"] == fund_name]
        dd_row = dd_df[dd_df["scheme_name"] == fund_name]
        te_row = te_df[te_df["scheme_name"] == fund_name]

        row["3Y CAGR"] = f"{cagr_row['cagr_3yr'].values[0]*100:.1f}%" if len(cagr_row) else "N/A"
        row["5Y CAGR"] = f"{cagr_row['cagr_5yr'].values[0]*100:.1f}%" if len(cagr_row) and not pd.isna(cagr_row['cagr_5yr'].values[0]) else "N/A"
        row["Sharpe"] = f"{sharpe_row['sharpe_ratio'].values[0]:.2f}" if len(sharpe_row) else "N/A"
        row["Sortino"] = f"{sortino_row['sortino_ratio'].values[0]:.2f}" if len(sortino_row) else "N/A"
        row["Alpha"] = f"{ab_row['alpha_annual'].values[0]*100:.2f}%" if len(ab_row) else "N/A"
        row["Beta"] = f"{ab_row['beta'].values[0]:.3f}" if len(ab_row) else "N/A"
        row["Max Drawdown"] = f"{dd_row['max_drawdown_pct'].values[0]:.1f}%" if len(dd_row) else "N/A"
        row["Tracking Error"] = f"{te_row['tracking_error'].values[0]:.4f}" if len(te_row) else "N/A"
        row["Score"] = f"{sc_row['composite_score'].values[0]:.1f}" if len(sc_row) else "N/A"

        metrics_to_compare.append(row)

    comp_table = pd.DataFrame(metrics_to_compare).set_index("Fund").T
    comp_table.index.name = "Metric"

    tc1, tc2 = st.columns([1, 1])
    with tc1:
        st.markdown("##### Side-by-Side Comparison")
        st.dataframe(comp_table, use_container_width=True)

    with tc2:
        # Radar chart
        sc_a = scorecard[scorecard["scheme_name"] == fund_a]
        sc_b = scorecard[scorecard["scheme_name"] == fund_b]
        if not sc_a.empty and not sc_b.empty:
            # Normalise metrics to 0-100 scale for radar
            all_sc = scorecard.copy()
            radar_metrics = ["cagr_3yr", "sharpe_ratio", "alpha_annual",
                             "expense_ratio_pct", "max_drawdown_pct"]
            radar_labels = ["3Y CAGR", "Sharpe", "Alpha", "Low Expense", "Low Drawdown"]

            vals_dict = {}
            for fund_name, sc_row in [(fund_a, sc_a), (fund_b, sc_b)]:
                vals = []
                for metric in radar_metrics:
                    if metric in sc_row.columns:
                        v = sc_row[metric].values[0]
                        col_min = all_sc[metric].min()
                        col_max = all_sc[metric].max()
                        if metric in ["expense_ratio_pct", "max_drawdown_pct"]:
                            norm = (1 - (v - col_min) / (col_max - col_min + 1e-9)) * 100
                        else:
                            norm = ((v - col_min) / (col_max - col_min + 1e-9)) * 100
                        vals.append(max(0, min(100, norm)))
                    else:
                        vals.append(50)
                vals_dict[fund_name[:30]] = vals

            fig = radar_chart(radar_labels, vals_dict,
                              title="Fund Comparison Radar", height=420)
            st.plotly_chart(fig, use_container_width=True)
elif fund_a == fund_b:
    st.warning("Please select two different funds to compare.")

# ═════════════════════════════════════════════════════════════
# BENCHMARK QUICK COMPARISON
# ═════════════════════════════════════════════════════════════
st.markdown(f'<div class="section-header">Benchmark Quick Comparison</div>', unsafe_allow_html=True)

bq1, bq2 = st.columns(2)
with bq1:
    bench_fund = st.selectbox("Select Fund", all_funds, key="bench_fund")
with bq2:
    bench_idx = st.selectbox("Select Benchmark", ["NIFTY50", "NIFTY100", "NIFTY_MIDCAP150"],
                             key="bench_idx")

if bench_fund:
    bench_data = get_benchmark_data()
    nav_data = get_nav_data()

    fund_code = scorecard[scorecard["scheme_name"] == bench_fund]["amfi_code"]
    if not fund_code.empty:
        code = fund_code.values[0]
        fund_nav = nav_data[nav_data["amfi_code"] == code].sort_values("date")
        bench_nav = bench_data[bench_data["index_name"] == bench_idx].sort_values("date")

        if not fund_nav.empty and not bench_nav.empty:
            # Growth chart
            series = {
                bench_fund[:35]: fund_nav.rename(columns={"nav": "value"}),
                bench_idx: bench_nav.rename(columns={"close_value": "value"}),
            }
            fig = growth_chart(
                series, "date", "value",
                title=f"Growth of Rs.100 -- {bench_fund[:30]} vs {bench_idx}",
                dash_keys=[bench_idx],
            )
            st.plotly_chart(fig, use_container_width=True)

            # Metrics table
            fund_cagr = cagr_df[cagr_df["scheme_name"] == bench_fund] if "scheme_name" in cagr_df.columns else cagr_df.merge(
                fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
            ).pipe(lambda d: d[d["scheme_name"] == bench_fund])
            ab_row = ab_df[ab_df["scheme_name"] == bench_fund]
            te_row = te_df[te_df["scheme_name"] == bench_fund]

            bench_metrics = {
                "Fund CAGR (3Y)": f"{fund_cagr['cagr_3yr'].values[0]*100:.1f}%" if len(fund_cagr) else "N/A",
                "Alpha": f"{ab_row['alpha_annual'].values[0]*100:.2f}%" if len(ab_row) else "N/A",
                "Beta": f"{ab_row['beta'].values[0]:.3f}" if len(ab_row) else "N/A",
                "Tracking Error": f"{te_row['tracking_error'].values[0]:.4f}" if len(te_row) else "N/A",
            }
            bm_df = pd.DataFrame(bench_metrics.items(), columns=["Metric", "Value"])
            st.dataframe(bm_df, use_container_width=True, hide_index=True)

# ── Export ──────────────────────────────────────────────────
with st.expander("Download Data"):
    st.download_button("Download Scorecard (CSV)", scorecard.to_csv(index=False),
                       "fund_scorecard.csv", "text/csv")
    st.download_button("Download Sharpe (CSV)", sharpe_df.to_csv(index=False),
                       "sharpe_values.csv", "text/csv")
    st.download_button("Download CAGR (CSV)", cagr_df.to_csv(index=False),
                       "cagr_report.csv", "text/csv")
