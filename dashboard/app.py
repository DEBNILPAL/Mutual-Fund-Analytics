"""
Bluestock MF Analytics Dashboard
=================================
Day 5 -- Production-grade 4-page Streamlit Dashboard
Author: DEBNIL PAL

Run:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure imports resolve from dashboard root
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(
    page_title="Bluestock MF Analytics",
    page_icon=":material/trending_up:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config.theme import (
    CUSTOM_CSS, PRIMARY, SECONDARY, kpi_card_html,
    spotlight_card_html, status_bar_html,
)
from utils.database import (
    db_status, get_fund_master, get_scorecard,
    get_sip_data, get_aum_data, get_industry_folios,
    get_transactions,
)

# ── Inject CSS ──────────────────────────────────────────────
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align:center; margin-bottom:20px;">
            <h2 style="color:{PRIMARY}; margin:0;">Bluestock MF</h2>
            <p style="color:#6B7280; font-size:12px; margin:2px 0;">
                Mutual Fund Analytics Platform
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # Navigation info
    st.markdown("##### Dashboard Pages")
    st.markdown("""
    1. **Market Overview** -- Industry KPIs
    2. **Fund Performance** -- Risk & Returns
    3. **Investor Demographics** -- Investor Analysis
    4. **Portfolio Analytics** -- Holdings & Benchmarks
    """)
    st.divider()

    # Global filters
    st.markdown("##### Global Filters")
    fund_master = get_fund_master()
    all_amcs = sorted(fund_master["fund_house"].unique().tolist())
    selected_amc = st.multiselect("AMC", all_amcs, default=[], key="global_amc")

    all_categories = sorted(fund_master["category"].unique().tolist())
    selected_cat = st.multiselect("Category", all_categories, default=[], key="global_cat")

    st.divider()
    st.markdown(
        '<p style="text-align:center; font-size:11px; color:#9CA3AF;">'
        'Day 5 Capstone | Bluestock Fintech</p>',
        unsafe_allow_html=True,
    )

# ── Executive Dashboard Header ──────────────────────────────
st.markdown(
    f'<h1 style="color:{PRIMARY}; margin-bottom:4px;">'
    'Bluestock Mutual Fund Analytics</h1>'
    '<p style="color:#6B7280; margin-top:0;">Production Dashboard -- Day 5 Capstone</p>',
    unsafe_allow_html=True,
)

# Status bar
info = db_status()
active_filters = []
if selected_amc:
    active_filters.append(f"AMC: {len(selected_amc)}")
if selected_cat:
    active_filters.append(f"Cat: {', '.join(selected_cat)}")
filter_str = " | ".join(active_filters) if active_filters else "None"
st.markdown(
    status_bar_html(info["status"], info["last_refresh"],
                    info["total_rows"], filter_str),
    unsafe_allow_html=True,
)

# ── Executive KPI Row ───────────────────────────────────────
aum_df = get_aum_data()
sip_df = get_sip_data()
folio_df = get_industry_folios()
tx_df = get_transactions()
scorecard = get_scorecard()

# Compute KPIs
total_aum = aum_df[aum_df["date"] == aum_df["date"].max()]["aum_lakh_crore"].sum()
latest_sip = sip_df.sort_values("date").iloc[-1] if not sip_df.empty else None
latest_folio = folio_df.sort_values("date").iloc[-1] if not folio_df.empty else None
total_investors = tx_df["investor_id"].nunique() if not tx_df.empty else 0
total_tx = len(tx_df)
best_fund = scorecard.sort_values("composite_score", ascending=False).iloc[0] if not scorecard.empty else None

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(kpi_card_html("Industry AUM", f"Rs.{total_aum:.1f}L Cr"), unsafe_allow_html=True)
with k2:
    schemes = int(aum_df[aum_df["date"] == aum_df["date"].max()]["num_schemes"].sum()) if not aum_df.empty else 0
    st.markdown(kpi_card_html("Total Schemes", f"{schemes:,}"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card_html("Total Investors", f"{total_investors:,}"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card_html("Total Transactions", f"{total_tx:,}"), unsafe_allow_html=True)
with k5:
    sip_val = f"Rs.{latest_sip['sip_inflow_crore']:,.0f} Cr" if latest_sip is not None else "N/A"
    st.markdown(kpi_card_html("Latest SIP Inflow", sip_val), unsafe_allow_html=True)
with k6:
    score_val = f"{best_fund['composite_score']:.1f}" if best_fund is not None else "N/A"
    st.markdown(kpi_card_html("Best Fund Score", score_val), unsafe_allow_html=True)

# ── Top Fund Spotlight ──────────────────────────────────────
st.markdown("")
if best_fund is not None:
    st.markdown(
        spotlight_card_html(
            fund_name=best_fund["scheme_name"],
            score=best_fund["composite_score"],
            sharpe=best_fund.get("sharpe_ratio", 0),
            cagr_3yr=best_fund.get("cagr_3yr", 0) * 100,
            category=best_fund.get("category", "Equity"),
        ),
        unsafe_allow_html=True,
    )

st.markdown("")
st.info("Select a page from the sidebar navigation to explore detailed analytics.", icon=":material/arrow_back:")
