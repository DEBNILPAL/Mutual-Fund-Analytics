"""
Bluestock MF Dashboard -- Dynamic Insight Engine
=================================================
Generates human-readable insight strings from data.
"""
from __future__ import annotations

import pandas as pd


# ── Market Overview Insights ────────────────────────────────
def market_insights(aum_df: pd.DataFrame, sip_df: pd.DataFrame,
                    folio_df: pd.DataFrame) -> list[str]:
    """Generate dynamic insights for the Market Overview page."""
    insights = []

    # Top AMC by AUM
    if not aum_df.empty:
        latest = aum_df[aum_df["date"] == aum_df["date"].max()]
        if not latest.empty:
            top = latest.nlargest(1, "aum_lakh_crore").iloc[0]
            insights.append(
                f"<b>{top['fund_house']}</b> leads the industry with "
                f"<b>Rs.{top['aum_lakh_crore']:.1f} Lakh Crore</b> AUM, "
                f"managing {int(top['num_schemes'])} schemes."
            )

    # SIP milestone
    if not sip_df.empty:
        latest_sip = sip_df.sort_values("date").iloc[-1]
        insights.append(
            f"Monthly SIP inflows reached <b>Rs.{latest_sip['sip_inflow_crore']:,.0f} Crore</b> "
            f"with <b>{latest_sip['active_sip_accounts_crore']:.2f} Crore</b> active accounts "
            f"-- a historic milestone for the Indian MF industry."
        )

    # Folio growth
    if not folio_df.empty and len(folio_df) >= 2:
        latest_f = folio_df.sort_values("date").iloc[-1]
        prev_f = folio_df.sort_values("date").iloc[-2]
        growth = latest_f["total_folios_crore"] - prev_f["total_folios_crore"]
        insights.append(
            f"Total industry folios stand at <b>{latest_f['total_folios_crore']:.2f} Crore</b>, "
            f"growing by <b>{growth:.2f} Crore</b> in the latest period."
        )

    return insights


# ── Fund Performance Insights ──────────────────────────────
def performance_insights(scorecard: pd.DataFrame, sharpe_df: pd.DataFrame,
                         cagr_df: pd.DataFrame, dd_df: pd.DataFrame) -> list[str]:
    """Generate dynamic insights for the Fund Performance page."""
    insights = []

    if not scorecard.empty:
        top = scorecard.sort_values("composite_score", ascending=False).iloc[0]
        insights.append(
            f"<b>{top['scheme_name']}</b> ranks #1 with a composite score of "
            f"<b>{top['composite_score']:.1f}/100</b> ({top['tier']} tier)."
        )

    if not sharpe_df.empty:
        best = sharpe_df.sort_values("sharpe_ratio", ascending=False).iloc[0]
        insights.append(
            f"<b>{best['scheme_name']}</b> delivers the highest risk-adjusted return "
            f"with a Sharpe Ratio of <b>{best['sharpe_ratio']:.2f}</b>."
        )

    if not cagr_df.empty:
        best3 = cagr_df.sort_values("cagr_3yr", ascending=False).iloc[0]
        insights.append(
            f"<b>{best3['scheme_name']}</b> leads 3-Year growth at "
            f"<b>{best3['cagr_3yr']*100:.1f}%</b> CAGR."
        )

    if not dd_df.empty:
        worst = dd_df.sort_values("max_drawdown_pct").iloc[0]
        insights.append(
            f"<b>{worst['scheme_name']}</b> experienced the deepest drawdown of "
            f"<b>{worst['max_drawdown_pct']:.1f}%</b>."
        )

    return insights


# ── Investor Demographics Insights ─────────────────────────
def investor_insights(tx_df: pd.DataFrame) -> list[str]:
    """Generate dynamic insights for the Investor Demographics page."""
    insights = []
    if tx_df.empty:
        return insights

    # SIP vs Lumpsum
    type_counts = tx_df["transaction_type"].value_counts()
    if "SIP" in type_counts.index:
        sip_pct = type_counts["SIP"] / type_counts.sum() * 100
        insights.append(
            f"SIP transactions account for <b>{sip_pct:.1f}%</b> of all transactions, "
            f"reflecting strong systematic investment discipline."
        )

    # Gender
    gender_counts = tx_df["gender"].value_counts()
    if "Male" in gender_counts.index and "Female" in gender_counts.index:
        f_pct = gender_counts["Female"] / gender_counts.sum() * 100
        insights.append(
            f"Female investors represent <b>{f_pct:.1f}%</b> of transactions -- "
            f"indicating growing participation but room for improvement."
        )

    # T30/B30
    tier_counts = tx_df["city_tier"].value_counts()
    if "B30" in tier_counts.index:
        b30_pct = tier_counts["B30"] / tier_counts.sum() * 100
        insights.append(
            f"B30 (Beyond-Top-30) cities contribute <b>{b30_pct:.1f}%</b> of transactions, "
            f"signalling strong Tier-2/3 city adoption."
        )

    # Top age group
    age_counts = tx_df["age_group"].value_counts()
    if not age_counts.empty:
        top_age = age_counts.index[0]
        top_pct = age_counts.iloc[0] / age_counts.sum() * 100
        insights.append(
            f"The <b>{top_age}</b> age group dominates with <b>{top_pct:.1f}%</b> "
            f"of all transactions."
        )

    return insights


# ── Portfolio Insights ─────────────────────────────────────
def portfolio_insights(portfolio_df: pd.DataFrame) -> list[str]:
    """Generate dynamic insights for the Portfolio page."""
    insights = []
    if portfolio_df.empty:
        return insights

    # Top sector
    sector_weights = portfolio_df.groupby("sector")["weight_pct"].sum().sort_values(ascending=False)
    if not sector_weights.empty:
        top_sector = sector_weights.index[0]
        insights.append(
            f"<b>{top_sector}</b> is the most allocated sector across all fund portfolios "
            f"with a total weight of <b>{sector_weights.iloc[0]:.1f}%</b>."
        )

    # Top holding
    top_holding = portfolio_df.nlargest(1, "weight_pct")
    if not top_holding.empty:
        h = top_holding.iloc[0]
        insights.append(
            f"<b>{h['stock_name']}</b> ({h['sector']}) carries the highest single-stock "
            f"weight at <b>{h['weight_pct']:.1f}%</b>."
        )

    # Concentration
    n_sectors = portfolio_df["sector"].nunique()
    insights.append(
        f"Portfolio holdings span <b>{n_sectors}</b> sectors, providing broad diversification."
    )

    return insights
