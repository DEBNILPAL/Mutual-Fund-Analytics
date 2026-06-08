"""
Page 3 -- Investor Demographics
================================
Age | Gender | Income | SIP vs Lumpsum | State-wise |
T30 vs B30 | Age vs Investment | Redemption Patterns
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config.theme import (
    CUSTOM_CSS, PRIMARY, SECONDARY, CHART_PALETTE,
    kpi_card_html, status_bar_html, insight_html,
)
from utils.database import db_status, get_transactions, get_fund_master
from utils.charts import bar_chart, donut_chart, scatter_chart, box_chart
from utils.insights import investor_insights

st.set_page_config(page_title="Investor Demographics | Bluestock MF", page_icon=":material/trending_up:", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────
st.markdown(f'<h1 style="color:{PRIMARY};">Investor Demographics & Behaviour</h1>', unsafe_allow_html=True)

info = db_status()
st.markdown(status_bar_html(info["status"], info["last_refresh"], info["total_rows"]), unsafe_allow_html=True)

# ── Load Data ───────────────────────────────────────────────
tx_df = get_transactions()

# ── KPI Cards ───────────────────────────────────────────────
total_investors = tx_df["investor_id"].nunique()
total_tx = len(tx_df)
total_volume = tx_df["amount_inr"].sum()
sip_count = len(tx_df[tx_df["transaction_type"] == "SIP"])
avg_ticket = tx_df["amount_inr"].mean()

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(kpi_card_html("Total Investors", f"{total_investors:,}"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card_html("Total Transactions", f"{total_tx:,}"), unsafe_allow_html=True)
with k3:
    if total_volume > 1e7:
        st.markdown(kpi_card_html("Total Volume", f"Rs.{total_volume/1e7:.1f} Cr"), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card_html("Total Volume", f"Rs.{total_volume/1e5:.1f} L"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card_html("SIP Transactions", f"{sip_count:,}"), unsafe_allow_html=True)
with k5:
    st.markdown(kpi_card_html("Avg Ticket Size", f"Rs.{avg_ticket:,.0f}"), unsafe_allow_html=True)

st.markdown("")

# ── Insights ────────────────────────────────────────────────
insights = investor_insights(tx_df)
if insights:
    with st.expander("Key Insights", expanded=True):
        for ins in insights:
            st.markdown(insight_html(ins), unsafe_allow_html=True)

# ── Charts ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Demographics", "Geography", "Behaviour"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        # Age Distribution
        age_counts = tx_df["age_group"].value_counts().reset_index()
        age_counts.columns = ["Age Group", "Count"]
        age_order = ["18-25", "26-35", "36-45", "46-55", "56+"]
        age_counts["sort_key"] = age_counts["Age Group"].map(
            {v: i for i, v in enumerate(age_order)}
        )
        age_counts = age_counts.sort_values("sort_key").drop(columns="sort_key")
        fig = bar_chart(age_counts, "Age Group", "Count",
                        title="Transaction Count by Age Group")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Gender Distribution
        gender_counts = tx_df["gender"].value_counts().reset_index()
        gender_counts.columns = ["Gender", "Count"]
        fig = donut_chart(gender_counts, "Gender", "Count",
                          title="Gender Distribution")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        # Income Distribution
        income_bins = [0, 5, 10, 20, 50, 100, float("inf")]
        income_labels = ["<5L", "5-10L", "10-20L", "20-50L", "50L-1Cr", ">1Cr"]
        tx_df["income_bin"] = pd.cut(
            tx_df["annual_income_lakh"], bins=income_bins,
            labels=income_labels, right=False,
        )
        income_counts = tx_df["income_bin"].value_counts().reset_index()
        income_counts.columns = ["Income Range", "Count"]
        fig = bar_chart(income_counts, "Income Range", "Count",
                        title="Investor Income Distribution")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        # SIP vs Lumpsum
        type_counts = tx_df["transaction_type"].value_counts().reset_index()
        type_counts.columns = ["Type", "Count"]
        fig = donut_chart(type_counts, "Type", "Count",
                          title="SIP vs Lumpsum vs Redemption")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        # State-wise Transactions
        state_counts = tx_df["state"].value_counts().reset_index().head(12)
        state_counts.columns = ["State", "Transactions"]
        fig = bar_chart(state_counts, "Transactions", "State",
                        title="State-wise Transaction Volume",
                        orientation="h")
        fig.update_layout(height=480)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # T30 vs B30
        tier_counts = tx_df["city_tier"].value_counts().reset_index()
        tier_counts.columns = ["City Tier", "Count"]
        fig = donut_chart(tier_counts, "City Tier", "Count",
                          title="T30 (Top 30 Cities) vs B30 Distribution")
        st.plotly_chart(fig, use_container_width=True)

    # State-wise volume by transaction type
    st.markdown(f'<div class="section-header">State-wise Transaction Mix</div>', unsafe_allow_html=True)
    state_type = tx_df.groupby(["state", "transaction_type"]).size().reset_index(name="count")
    fig = px.bar(state_type, x="state", y="count", color="transaction_type",
                 barmode="stack", color_discrete_sequence=CHART_PALETTE,
                 title="Transaction Type by State")
    fig.update_layout(height=420, xaxis_title="State", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        # Age vs Investment Amount
        age_amount = tx_df.groupby("age_group")["amount_inr"].mean().reset_index()
        age_amount.columns = ["Age Group", "Avg Investment (Rs.)"]
        fig = bar_chart(age_amount, "Age Group", "Avg Investment (Rs.)",
                        title="Average Investment by Age Group")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Redemption Pattern
        redemptions = tx_df[tx_df["transaction_type"] == "Redemption"]
        if not redemptions.empty:
            red_by_age = redemptions.groupby("age_group").size().reset_index(name="Redemptions")
            fig = bar_chart(red_by_age, "age_group", "Redemptions",
                            title="Redemption Count by Age Group")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No redemption data available.")

    # Income vs Transaction Type
    st.markdown(f'<div class="section-header">Investment Patterns</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        income_type = tx_df.groupby(["income_bin", "transaction_type"]).size().reset_index(name="count")
        fig = px.bar(income_type, x="income_bin", y="count", color="transaction_type",
                     barmode="group", color_discrete_sequence=CHART_PALETTE,
                     title="Transaction Type by Income Range")
        fig.update_layout(height=400, xaxis_title="Income Range", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        # Gender by city tier
        gender_tier = tx_df.groupby(["gender", "city_tier"]).size().reset_index(name="count")
        fig = px.bar(gender_tier, x="gender", y="count", color="city_tier",
                     barmode="group", color_discrete_sequence=CHART_PALETTE,
                     title="Gender Distribution by City Tier")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# ── Export ──────────────────────────────────────────────────
with st.expander("Download Data"):
    st.download_button("Download Transactions (CSV)", tx_df.to_csv(index=False),
                       "investor_transactions.csv", "text/csv")
