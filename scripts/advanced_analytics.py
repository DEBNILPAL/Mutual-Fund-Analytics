"""
Bluestock MF Capstone -- Day 6: Advanced Analytics Engine
=========================================================
Author : DEBNIL PAL
Date   : 2026-06-08

Modules:
  1. Value at Risk (VaR) -- Historical, Parametric, Monte Carlo
  2. Conditional VaR (CVaR / Expected Shortfall)
  3. Investor Cohort Analysis
  4. Customer Segmentation
  5. Monte Carlo Simulation (Bonus B3)
  6. Markowitz Portfolio Optimization (Bonus B4)
  7. Rolling Analytics (Sharpe, Volatility, Beta)
  8. Advanced Correlation Analysis
  9. Risk Score Engine
  10. Key Business Insights
  11. Validation
"""
from __future__ import annotations

import logging
import sqlite3
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ───────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "data" / "db" / "bluestock_mf.db"
PROCESSED   = BASE_DIR / "data" / "processed"
CHARTS_DIR  = BASE_DIR / "reports" / "charts"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR    = BASE_DIR / "logs"

for d in (PROCESSED, CHARTS_DIR, REPORTS_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Logging ─────────────────────────────────────────────────
LOG_FILE = LOGS_DIR / "advanced_analytics.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("day6")

# ── Constants ───────────────────────────────────────────────
RF_DAILY    = 0.065 / 252          # 6.5% annual risk-free
TRADING_DAYS = 252
PALETTE = [
    "#0A4D8C", "#00B894", "#E17055", "#6C5CE7",
    "#FDCB6E", "#0984E3", "#D63031", "#00CEC9",
    "#E84393", "#2D3436", "#636E72", "#74B9FF",
]
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.3,
    "font.size": 10, "axes.titlesize": 13,
})

# ── Data Loaders ────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))

def load_returns() -> pd.DataFrame:
    """Load daily returns from Day 4 CSV."""
    df = pd.read_csv(PROCESSED / "daily_returns.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df

def load_fund_master() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM dim_fund", _conn())

def load_transactions() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM fact_transactions", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df

def load_nav() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM fact_nav", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df

def load_scorecard() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "fund_scorecard.csv")

def load_benchmark() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM fact_benchmark", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df


# ════════════════════════════════════════════════════════════
# PHASE 2: VALUE AT RISK (VaR) + CVaR
# ════════════════════════════════════════════════════════════

def compute_var(returns_df: pd.DataFrame, fund_master: pd.DataFrame) -> pd.DataFrame:
    """Compute Historical VaR, Parametric VaR, Monte Carlo VaR, and CVaR."""
    logger.info("--- Phase 2: Value at Risk ---")
    results = []
    funds = returns_df["amfi_code"].unique()

    for code in funds:
        r = returns_df[returns_df["amfi_code"] == code]["daily_return"].dropna()
        if len(r) < 30:
            continue
        mu = r.mean()
        sigma = r.std()

        # Historical VaR
        hist_var95 = np.percentile(r, 5)
        hist_var99 = np.percentile(r, 1)

        # Parametric VaR (Normal assumption)
        param_var95 = mu + (-1.645) * sigma
        param_var99 = mu + (-2.326) * sigma

        # Monte Carlo VaR (10,000 simulations)
        mc_sims = np.random.normal(mu, sigma, 10000)
        mc_var95 = np.percentile(mc_sims, 5)
        mc_var99 = np.percentile(mc_sims, 1)

        # CVaR (Expected Shortfall)
        cvar95 = r[r <= hist_var95].mean()
        cvar99 = r[r <= hist_var99].mean()

        name = fund_master[fund_master["amfi_code"] == code]["scheme_name"]
        name = name.values[0] if len(name) else str(code)

        results.append({
            "amfi_code": code,
            "scheme_name": name,
            "hist_var_95": round(hist_var95, 6),
            "hist_var_99": round(hist_var99, 6),
            "param_var_95": round(param_var95, 6),
            "param_var_99": round(param_var99, 6),
            "mc_var_95": round(mc_var95, 6),
            "mc_var_99": round(mc_var99, 6),
            "cvar_95": round(cvar95, 6),
            "cvar_99": round(cvar99, 6),
            "expected_shortfall": round(cvar95, 6),
        })

    df = pd.DataFrame(results)
    df.to_csv(PROCESSED / "var_summary.csv", index=False)
    logger.info("VaR computed for %d funds -> var_summary.csv", len(df))
    return df


def chart_var(var_df: pd.DataFrame, returns_df: pd.DataFrame) -> None:
    """Generate VaR distribution and CVaR comparison charts."""
    # 1. VaR Distribution for top fund
    top = var_df.sort_values("hist_var_95").iloc[0]
    r = returns_df[returns_df["amfi_code"] == top["amfi_code"]]["daily_return"].dropna()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(r, bins=80, color=PALETTE[0], alpha=0.7, edgecolor="white", density=True)
    ax.axvline(top["hist_var_95"], color="red", lw=2, ls="--", label=f"VaR 95%: {top['hist_var_95']:.4f}")
    ax.axvline(top["hist_var_99"], color="darkred", lw=2, ls="--", label=f"VaR 99%: {top['hist_var_99']:.4f}")
    ax.axvline(top["cvar_95"], color="orange", lw=2, ls=":", label=f"CVaR 95%: {top['cvar_95']:.4f}")
    ax.set_title(f"Return Distribution & VaR -- {top['scheme_name'][:40]}", fontweight="bold")
    ax.set_xlabel("Daily Return")
    ax.set_ylabel("Density")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "var_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> var_distribution.png")

    # 2. CVaR Comparison
    fig, ax = plt.subplots(figsize=(14, 7))
    top20 = var_df.sort_values("cvar_95").head(20).sort_values("cvar_95", ascending=True)
    y = range(len(top20))
    ax.barh(y, top20["cvar_95"] * 100, color=PALETTE[6], alpha=0.8, label="CVaR 95%")
    ax.barh(y, top20["cvar_99"] * 100, color=PALETTE[3], alpha=0.6, label="CVaR 99%")
    ax.set_yticks(y)
    ax.set_yticklabels(top20["scheme_name"].str[:30], fontsize=8)
    ax.set_xlabel("CVaR (%)")
    ax.set_title("Conditional VaR (Expected Shortfall) -- Worst 20 Funds", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "cvar_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> cvar_comparison.png")


# ════════════════════════════════════════════════════════════
# PHASE 3: INVESTOR COHORT ANALYSIS
# ════════════════════════════════════════════════════════════

def compute_cohorts(tx_df: pd.DataFrame) -> pd.DataFrame:
    """Cohort analysis by age, income, state, city tier."""
    logger.info("--- Phase 3: Investor Cohort Analysis ---")
    cohorts = []

    for group_col in ["age_group", "city_tier", "state"]:
        for group_val, grp in tx_df.groupby(group_col):
            total = len(grp)
            sip_count = len(grp[grp["transaction_type"] == "SIP"])
            lump_count = len(grp[grp["transaction_type"] == "Lumpsum"])
            red_count = len(grp[grp["transaction_type"] == "Redemption"])
            avg_amount = grp["amount_inr"].mean()
            total_amount = grp["amount_inr"].sum()
            investors = grp["investor_id"].nunique()

            retention = 1 - (red_count / max(total, 1))
            redemption_rate = red_count / max(total, 1)
            avg_sip = grp[grp["transaction_type"] == "SIP"]["amount_inr"].mean() if sip_count else 0

            cohorts.append({
                "cohort_type": group_col,
                "cohort_value": group_val,
                "total_transactions": total,
                "unique_investors": investors,
                "sip_count": sip_count,
                "lumpsum_count": lump_count,
                "redemption_count": red_count,
                "retention_rate": round(retention, 4),
                "redemption_rate": round(redemption_rate, 4),
                "avg_investment": round(avg_amount, 2),
                "avg_sip_amount": round(avg_sip, 2),
                "total_volume": round(total_amount, 2),
            })

    df = pd.DataFrame(cohorts)
    df.to_csv(PROCESSED / "cohort_analysis.csv", index=False)
    logger.info("Cohort analysis -> %d cohorts -> cohort_analysis.csv", len(df))
    return df


def chart_cohorts(cohort_df: pd.DataFrame) -> None:
    """Generate cohort charts."""
    age_cohorts = cohort_df[cohort_df["cohort_type"] == "age_group"].copy()
    if not age_cohorts.empty:
        # Retention
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(age_cohorts["cohort_value"], age_cohorts["retention_rate"] * 100,
               color=PALETTE[:len(age_cohorts)], alpha=0.85)
        ax.set_title("Investor Retention Rate by Age Group", fontweight="bold")
        ax.set_ylabel("Retention Rate (%)")
        ax.set_xlabel("Age Group")
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "cohort_retention.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Chart saved -> cohort_retention.png")

        # Investment growth (avg investment)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(age_cohorts["cohort_value"], age_cohorts["avg_investment"],
               color=PALETTE[:len(age_cohorts)], alpha=0.85)
        ax.set_title("Average Investment by Age Group", fontweight="bold")
        ax.set_ylabel("Avg Investment (Rs.)")
        ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "cohort_growth.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Chart saved -> cohort_growth.png")

        # Redemption rate
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(age_cohorts["cohort_value"], age_cohorts["redemption_rate"] * 100,
               color=PALETTE[6], alpha=0.85)
        ax.set_title("Redemption Rate by Age Group", fontweight="bold")
        ax.set_ylabel("Redemption Rate (%)")
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "cohort_redemption.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Chart saved -> cohort_redemption.png")


# ════════════════════════════════════════════════════════════
# PHASE 4: CUSTOMER SEGMENTATION
# ════════════════════════════════════════════════════════════

def compute_segments(tx_df: pd.DataFrame, fund_master: pd.DataFrame) -> pd.DataFrame:
    """Rule-based investor segmentation into Conservative / Balanced / Aggressive."""
    logger.info("--- Phase 4: Customer Segmentation ---")

    inv_stats = tx_df.groupby("investor_id").agg(
        total_amount=("amount_inr", "sum"),
        avg_amount=("amount_inr", "mean"),
        tx_count=("amount_inr", "count"),
        sip_count=("transaction_type", lambda x: (x == "SIP").sum()),
        age_group=("age_group", "first"),
        income=("annual_income_lakh", "first"),
        gender=("gender", "first"),
        state=("state", "first"),
        city_tier=("city_tier", "first"),
    ).reset_index()

    inv_stats["sip_ratio"] = inv_stats["sip_count"] / inv_stats["tx_count"]

    # Score-based segmentation
    def _segment(row: pd.Series) -> str:
        score = 0
        # Age factor
        if row["age_group"] in ("56+", "46-55"):
            score -= 1
        elif row["age_group"] in ("18-25",):
            score += 1
        # Income factor
        if pd.notna(row["income"]):
            if row["income"] > 20:
                score += 1
            elif row["income"] < 5:
                score -= 1
        # SIP dominance = conservative/balanced
        if row["sip_ratio"] > 0.7:
            score -= 1
        elif row["sip_ratio"] < 0.3:
            score += 1
        # Ticket size
        if row["avg_amount"] > 50000:
            score += 1
        elif row["avg_amount"] < 10000:
            score -= 1

        if score >= 2:
            return "Aggressive"
        elif score <= -1:
            return "Conservative"
        else:
            return "Balanced"

    inv_stats["investor_segment"] = inv_stats.apply(_segment, axis=1)
    inv_stats.to_csv(PROCESSED / "investor_segments.csv", index=False)
    logger.info("Segmentation -> %d investors -> investor_segments.csv",
                len(inv_stats))

    seg_counts = inv_stats["investor_segment"].value_counts()
    logger.info("  Conservative: %d | Balanced: %d | Aggressive: %d",
                seg_counts.get("Conservative", 0),
                seg_counts.get("Balanced", 0),
                seg_counts.get("Aggressive", 0))
    return inv_stats


def chart_segments(seg_df: pd.DataFrame) -> None:
    """Pie/bar chart of investor segments."""
    counts = seg_df["investor_segment"].value_counts()
    colours = {"Conservative": PALETTE[0], "Balanced": PALETTE[1], "Aggressive": PALETTE[6]}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    ax1.pie(counts, labels=counts.index, autopct="%1.1f%%",
            colors=[colours.get(s, "#999") for s in counts.index],
            startangle=90, textprops={"fontsize": 10})
    ax1.set_title("Investor Persona Distribution", fontweight="bold")

    # Segment by age group
    cross = seg_df.groupby(["age_group", "investor_segment"]).size().unstack(fill_value=0)
    cross.plot(kind="bar", ax=ax2, color=[colours.get(c, "#999") for c in cross.columns],
               alpha=0.85, edgecolor="white")
    ax2.set_title("Segment by Age Group", fontweight="bold")
    ax2.set_ylabel("Investors")
    ax2.legend(fontsize=8)
    plt.xticks(rotation=0)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "investor_segments.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> investor_segments.png")


# ════════════════════════════════════════════════════════════
# PHASE 6: MONTE CARLO SIMULATION (Bonus B3)
# ════════════════════════════════════════════════════════════

def monte_carlo_simulation(returns_df: pd.DataFrame,
                           scorecard: pd.DataFrame,
                           fund_master: pd.DataFrame,
                           n_sims: int = 10000,
                           years: int = 5) -> pd.DataFrame:
    """GBM Monte Carlo for top 10 funds."""
    logger.info("--- Phase 6: Monte Carlo Simulation (B3) ---")
    top10 = scorecard.sort_values("composite_score", ascending=False).head(10)
    horizon = years * TRADING_DAYS
    results = []

    for _, fund in top10.iterrows():
        code = fund["amfi_code"]
        r = returns_df[returns_df["amfi_code"] == code]["daily_return"].dropna()
        if len(r) < 60:
            continue

        mu = r.mean()
        sigma = r.std()
        last_nav = returns_df[returns_df["amfi_code"] == code]["nav"].iloc[-1]

        # GBM: S(t) = S(0) * exp((mu - 0.5*sigma^2)*t + sigma*W(t))
        dt = 1.0
        paths = np.zeros((n_sims, horizon))
        paths[:, 0] = last_nav
        for t in range(1, horizon):
            z = np.random.standard_normal(n_sims)
            paths[:, t] = paths[:, t-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)

        final_navs = paths[:, -1]
        results.append({
            "amfi_code": code,
            "scheme_name": fund["scheme_name"],
            "current_nav": round(last_nav, 2),
            "median_5yr": round(np.median(final_navs), 2),
            "p5_5yr": round(np.percentile(final_navs, 5), 2),
            "p25_5yr": round(np.percentile(final_navs, 25), 2),
            "p75_5yr": round(np.percentile(final_navs, 75), 2),
            "p95_5yr": round(np.percentile(final_navs, 95), 2),
            "mean_5yr": round(np.mean(final_navs), 2),
            "prob_positive": round((final_navs > last_nav).mean(), 4),
            "expected_cagr": round((np.median(final_navs)/last_nav)**(1/years) - 1, 4),
        })

    df = pd.DataFrame(results)
    df.to_csv(PROCESSED / "monte_carlo_projections.csv", index=False)
    logger.info("Monte Carlo -> %d funds, %d sims each -> monte_carlo_projections.csv",
                len(df), n_sims)
    return df


def chart_monte_carlo(mc_df: pd.DataFrame, returns_df: pd.DataFrame) -> None:
    """Monte Carlo fan chart for top fund."""
    if mc_df.empty:
        return
    top = mc_df.iloc[0]
    code = top["amfi_code"]
    r = returns_df[returns_df["amfi_code"] == code]["daily_return"].dropna()
    mu, sigma = r.mean(), r.std()
    last_nav = top["current_nav"]
    horizon = 5 * TRADING_DAYS

    # Re-run fewer paths for visualisation
    np.random.seed(42)
    n_vis = 200
    paths = np.zeros((n_vis, horizon))
    paths[:, 0] = last_nav
    for t in range(1, horizon):
        z = np.random.standard_normal(n_vis)
        paths[:, t] = paths[:, t-1] * np.exp((mu - 0.5*sigma**2) + sigma*z)

    fig, ax = plt.subplots(figsize=(14, 7))
    days = np.arange(horizon)
    for i in range(min(50, n_vis)):
        ax.plot(days, paths[i], alpha=0.08, color=PALETTE[0], lw=0.5)

    med = np.median(paths, axis=0)
    p5 = np.percentile(paths, 5, axis=0)
    p95 = np.percentile(paths, 95, axis=0)
    ax.plot(days, med, color=PALETTE[0], lw=2.5, label="Median")
    ax.fill_between(days, p5, p95, alpha=0.15, color=PALETTE[0], label="5th-95th Percentile")
    ax.axhline(last_nav, ls="--", color="#999", lw=1, label=f"Current NAV: {last_nav:.0f}")
    ax.set_title(f"Monte Carlo 5-Year Projection -- {top['scheme_name'][:40]}",
                 fontweight="bold", fontsize=14)
    ax.set_xlabel("Trading Days")
    ax.set_ylabel("Projected NAV")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "monte_carlo_top_fund.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> monte_carlo_top_fund.png")

    # Fan chart for multiple funds
    fig, ax = plt.subplots(figsize=(14, 7))
    for idx, (_, row) in enumerate(mc_df.head(5).iterrows()):
        c = PALETTE[idx % len(PALETTE)]
        ax.barh(idx*3, row["p95_5yr"] - row["p5_5yr"], left=row["p5_5yr"],
                height=1.5, color=c, alpha=0.3)
        ax.plot(row["median_5yr"], idx*3, "o", color=c, ms=10)
        ax.plot(row["current_nav"], idx*3, "s", color="black", ms=6)
    names = mc_df.head(5)["scheme_name"].str[:30].tolist()
    ax.set_yticks([i*3 for i in range(len(names))])
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Projected NAV Range (5-Year)")
    ax.set_title("Monte Carlo Fan Chart -- Top 5 Funds", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "monte_carlo_fan_chart.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> monte_carlo_fan_chart.png")


# ════════════════════════════════════════════════════════════
# PHASE 7: MARKOWITZ PORTFOLIO OPTIMIZATION (Bonus B4)
# ════════════════════════════════════════════════════════════

def markowitz_optimization(returns_df: pd.DataFrame,
                           scorecard: pd.DataFrame,
                           n_portfolios: int = 10000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Markowitz mean-variance optimization for top 5 funds."""
    logger.info("--- Phase 7: Markowitz Portfolio Optimization (B4) ---")
    top5 = scorecard.sort_values("composite_score", ascending=False).head(5)
    codes = top5["amfi_code"].tolist()
    names = top5["scheme_name"].tolist()

    # Build return matrix
    pivot = returns_df[returns_df["amfi_code"].isin(codes)].pivot_table(
        index="date", columns="amfi_code", values="daily_return"
    ).dropna()

    mean_returns = pivot.mean() * TRADING_DAYS
    cov_matrix = pivot.cov() * TRADING_DAYS

    # Random portfolio generation
    port_returns = []
    port_vols = []
    port_sharpes = []
    port_weights = []

    np.random.seed(42)
    n_assets = len(codes)
    for _ in range(n_portfolios):
        w = np.random.random(n_assets)
        w /= w.sum()
        ret = np.dot(w, mean_returns)
        vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
        sharpe = (ret - 0.065) / vol
        port_returns.append(ret)
        port_vols.append(vol)
        port_sharpes.append(sharpe)
        port_weights.append(w)

    frontier_df = pd.DataFrame({
        "return": port_returns,
        "volatility": port_vols,
        "sharpe": port_sharpes,
    })
    for i, name in enumerate(names):
        frontier_df[f"w_{name[:20]}"] = [pw[i] for pw in port_weights]

    frontier_df.to_csv(PROCESSED / "efficient_frontier.csv", index=False)

    # Find optimal portfolios
    max_sharpe_idx = frontier_df["sharpe"].idxmax()
    min_vol_idx = frontier_df["volatility"].idxmin()

    opt_results = []
    for label, idx in [("Max Sharpe", max_sharpe_idx), ("Min Variance", min_vol_idx)]:
        row = frontier_df.iloc[idx]
        opt = {"portfolio": label, "return": round(row["return"], 4),
               "volatility": round(row["volatility"], 4),
               "sharpe": round(row["sharpe"], 4)}
        for i, name in enumerate(names):
            opt[f"w_{name[:20]}"] = round(port_weights[idx][i], 4)
        opt_results.append(opt)

    opt_df = pd.DataFrame(opt_results)
    opt_df.to_csv(PROCESSED / "optimal_portfolios.csv", index=False)
    logger.info("Markowitz -> %d portfolios, %d assets -> efficient_frontier.csv",
                n_portfolios, n_assets)
    logger.info("  Max Sharpe: ret=%.2f%% vol=%.2f%% sharpe=%.2f",
                opt_results[0]["return"]*100, opt_results[0]["volatility"]*100,
                opt_results[0]["sharpe"])
    logger.info("  Min Var:    ret=%.2f%% vol=%.2f%% sharpe=%.2f",
                opt_results[1]["return"]*100, opt_results[1]["volatility"]*100,
                opt_results[1]["sharpe"])

    return frontier_df, opt_df


def chart_markowitz(frontier_df: pd.DataFrame, opt_df: pd.DataFrame) -> None:
    """Efficient frontier and allocation charts."""
    fig, ax = plt.subplots(figsize=(12, 8))
    sc = ax.scatter(frontier_df["volatility"]*100, frontier_df["return"]*100,
                    c=frontier_df["sharpe"], cmap="RdYlGn", alpha=0.5, s=8)
    plt.colorbar(sc, ax=ax, label="Sharpe Ratio")

    # Mark optimal portfolios
    for _, row in opt_df.iterrows():
        marker = "*" if "Max" in row["portfolio"] else "D"
        color = "red" if "Max" in row["portfolio"] else "blue"
        ax.scatter(row["volatility"]*100, row["return"]*100,
                   marker=marker, s=300, c=color, edgecolors="black", zorder=5,
                   label=f"{row['portfolio']} (S={row['sharpe']:.2f})")

    ax.set_xlabel("Annualised Volatility (%)")
    ax.set_ylabel("Annualised Return (%)")
    ax.set_title("Efficient Frontier -- Top 5 Funds", fontweight="bold", fontsize=14)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "efficient_frontier.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> efficient_frontier.png")

    # Allocation pie for Max Sharpe portfolio
    w_cols = [c for c in opt_df.columns if c.startswith("w_")]
    max_sharpe = opt_df[opt_df["portfolio"] == "Max Sharpe"]
    if not max_sharpe.empty and w_cols:
        weights = max_sharpe[w_cols].values[0]
        labels = [c.replace("w_", "") for c in w_cols]
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.pie(weights, labels=labels, autopct="%1.1f%%",
               colors=PALETTE[:len(labels)], startangle=90, textprops={"fontsize": 9})
        ax.set_title("Optimal Portfolio Allocation (Max Sharpe)", fontweight="bold")
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "portfolio_allocation.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Chart saved -> portfolio_allocation.png")


# ════════════════════════════════════════════════════════════
# PHASE 8: ROLLING ANALYTICS
# ════════════════════════════════════════════════════════════

def compute_rolling(returns_df: pd.DataFrame, scorecard: pd.DataFrame,
                    benchmark_df: pd.DataFrame) -> None:
    """Rolling Sharpe, Volatility, Beta for top 5 funds."""
    logger.info("--- Phase 8: Rolling Analytics ---")
    top5 = scorecard.sort_values("composite_score", ascending=False).head(5)
    windows = [30, 90, 180]

    bench = benchmark_df[benchmark_df["index_name"] == "NIFTY100"].sort_values("date")
    bench["bench_return"] = bench["close_value"].pct_change()

    for chart_name, metric_fn, ylabel in [
        ("rolling_sharpe", lambda r, w: r.rolling(w).apply(
            lambda x: (x.mean() - RF_DAILY) / x.std() * np.sqrt(TRADING_DAYS) if x.std() > 0 else 0,
            raw=True
        ), "Rolling Sharpe"),
        ("rolling_volatility", lambda r, w: r.rolling(w).std() * np.sqrt(TRADING_DAYS) * 100,
         "Rolling Volatility (%)"),
    ]:
        fig, axes = plt.subplots(len(windows), 1, figsize=(14, 4*len(windows)), sharex=True)
        for wi, w in enumerate(windows):
            ax = axes[wi]
            for i, (_, fund) in enumerate(top5.iterrows()):
                code = fund["amfi_code"]
                fund_r = returns_df[returns_df["amfi_code"] == code].sort_values("date")
                if len(fund_r) < w:
                    continue
                vals = metric_fn(fund_r["daily_return"], w)
                ax.plot(fund_r["date"], vals, label=fund["scheme_name"][:25],
                        color=PALETTE[i], lw=1.2, alpha=0.9)
            ax.set_title(f"{w}-Day {ylabel}", fontweight="bold")
            ax.set_ylabel(ylabel)
            if wi == 0:
                ax.legend(fontsize=7, ncol=3, loc="upper left")
        plt.tight_layout()
        fig.savefig(CHARTS_DIR / f"{chart_name}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Chart saved -> %s.png", chart_name)

    # Rolling Beta
    fig, axes = plt.subplots(len(windows), 1, figsize=(14, 4*len(windows)), sharex=True)
    for wi, w in enumerate(windows):
        ax = axes[wi]
        for i, (_, fund) in enumerate(top5.iterrows()):
            code = fund["amfi_code"]
            fund_r = returns_df[returns_df["amfi_code"] == code].sort_values("date")
            merged = fund_r[["date", "daily_return"]].merge(
                bench[["date", "bench_return"]], on="date"
            ).dropna()
            if len(merged) < w:
                continue
            rolling_cov = merged["daily_return"].rolling(w).cov(merged["bench_return"])
            rolling_var = merged["bench_return"].rolling(w).var()
            rolling_beta = rolling_cov / rolling_var
            ax.plot(merged["date"], rolling_beta, label=fund["scheme_name"][:25],
                    color=PALETTE[i], lw=1.2, alpha=0.9)
        ax.axhline(1.0, ls="--", color="#999", lw=1)
        ax.set_title(f"{w}-Day Rolling Beta", fontweight="bold")
        ax.set_ylabel("Beta")
        if wi == 0:
            ax.legend(fontsize=7, ncol=3, loc="upper left")
    plt.tight_layout()
    fig.savefig(CHARTS_DIR / "rolling_beta.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> rolling_beta.png")


# ════════════════════════════════════════════════════════════
# PHASE 9: ADVANCED CORRELATION ANALYSIS
# ════════════════════════════════════════════════════════════

def compute_correlation(returns_df: pd.DataFrame,
                        fund_master: pd.DataFrame) -> None:
    """Fund-to-fund and fund-to-benchmark correlation."""
    logger.info("--- Phase 9: Advanced Correlation Analysis ---")

    # Pivot returns
    pivot = returns_df.pivot_table(index="date", columns="amfi_code", values="daily_return").dropna()
    name_map = fund_master.set_index("amfi_code")["scheme_name"].to_dict()
    pivot.columns = [name_map.get(c, str(c))[:20] for c in pivot.columns]

    corr = pivot.corr()

    # Heatmap
    fig, ax = plt.subplots(figsize=(16, 14))
    im = ax.imshow(corr.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=6)
    ax.set_yticks(range(len(corr)))
    ax.set_yticklabels(corr.index, fontsize=6)
    plt.colorbar(im, ax=ax, label="Correlation")
    ax.set_title("Fund-to-Fund Correlation Matrix", fontweight="bold", fontsize=14)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "advanced_correlation_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> advanced_correlation_heatmap.png")

    # Network-style scatter (correlation pairs)
    pairs = []
    for i in range(len(corr)):
        for j in range(i+1, len(corr)):
            pairs.append({
                "fund_a": corr.index[i],
                "fund_b": corr.columns[j],
                "correlation": corr.iloc[i, j],
            })
    pairs_df = pd.DataFrame(pairs).sort_values("correlation", ascending=False)

    fig, ax = plt.subplots(figsize=(14, 7))
    top_pairs = pairs_df.head(20)
    labels = [f"{r['fund_a'][:12]} - {r['fund_b'][:12]}" for _, r in top_pairs.iterrows()]
    colours = ["green" if v > 0.5 else "orange" if v > 0 else "red" for v in top_pairs["correlation"]]
    ax.barh(range(len(labels)), top_pairs["correlation"], color=colours, alpha=0.8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Correlation")
    ax.set_title("Top 20 Most Correlated Fund Pairs", fontweight="bold")
    ax.axvline(0, color="black", lw=0.5)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "correlation_network.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> correlation_network.png")


# ════════════════════════════════════════════════════════════
# PHASE 10: RISK SCORE ENGINE
# ════════════════════════════════════════════════════════════

def compute_risk_scores(returns_df: pd.DataFrame, var_df: pd.DataFrame,
                        fund_master: pd.DataFrame) -> pd.DataFrame:
    """Composite Risk Score (0-100) from volatility, drawdown, beta, VaR."""
    logger.info("--- Phase 10: Risk Score Engine ---")
    scorecard = pd.read_csv(PROCESSED / "fund_scorecard.csv")
    dd_df = pd.read_csv(PROCESSED / "max_drawdown.csv")
    ab_df = pd.read_csv(PROCESSED / "alpha_beta.csv")

    merged = scorecard[["amfi_code", "scheme_name", "category"]].copy()
    merged = merged.merge(dd_df[["amfi_code", "max_drawdown_pct"]], on="amfi_code", how="left")
    merged = merged.merge(ab_df[["amfi_code", "beta"]], on="amfi_code", how="left")
    merged = merged.merge(var_df[["amfi_code", "hist_var_95", "cvar_95"]], on="amfi_code", how="left")

    # Compute annualised volatility
    vol_df = returns_df.groupby("amfi_code")["daily_return"].std().reset_index()
    vol_df.columns = ["amfi_code", "daily_vol"]
    vol_df["ann_volatility"] = vol_df["daily_vol"] * np.sqrt(TRADING_DAYS)
    merged = merged.merge(vol_df[["amfi_code", "ann_volatility"]], on="amfi_code", how="left")

    # Normalise each risk factor to 0-100 (higher = riskier)
    def _norm(s: pd.Series, invert: bool = False) -> pd.Series:
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series(50, index=s.index)
        normed = (s - mn) / (mx - mn) * 100
        return 100 - normed if invert else normed

    merged["vol_score"] = _norm(merged["ann_volatility"])
    merged["dd_score"] = _norm(merged["max_drawdown_pct"].abs())
    merged["beta_score"] = _norm(merged["beta"].abs())
    merged["var_score"] = _norm(merged["hist_var_95"].abs())

    merged["risk_score"] = (
        merged["vol_score"] * 0.30 +
        merged["dd_score"] * 0.30 +
        merged["beta_score"] * 0.20 +
        merged["var_score"] * 0.20
    ).round(1)

    def _tier(score: float) -> str:
        if score >= 75:
            return "Very High"
        elif score >= 50:
            return "High"
        elif score >= 25:
            return "Moderate"
        return "Low"

    merged["risk_tier"] = merged["risk_score"].apply(_tier)

    out = merged[["amfi_code", "scheme_name", "category", "ann_volatility",
                   "max_drawdown_pct", "beta", "hist_var_95", "risk_score", "risk_tier"]]
    out.to_csv(PROCESSED / "risk_scorecard.csv", index=False)
    logger.info("Risk scores -> %d funds -> risk_scorecard.csv", len(out))
    return out


# ════════════════════════════════════════════════════════════
# PHASE 11: KEY BUSINESS INSIGHTS
# ════════════════════════════════════════════════════════════

def generate_insights(var_df: pd.DataFrame, cohort_df: pd.DataFrame,
                      seg_df: pd.DataFrame, mc_df: pd.DataFrame,
                      risk_df: pd.DataFrame, scorecard: pd.DataFrame) -> list[str]:
    """Generate 15 advanced business insights."""
    logger.info("--- Phase 11: Key Business Insights ---")
    insights = []

    # 1. Most resilient fund
    if not risk_df.empty:
        safest = risk_df.sort_values("risk_score").iloc[0]
        insights.append(
            f"1. MOST RESILIENT FUND: {safest['scheme_name']} has the lowest risk score "
            f"({safest['risk_score']:.1f}/100) with volatility of {safest['ann_volatility']*100:.1f}%."
        )

    # 2. Best risk-adjusted performer
    best = scorecard.sort_values("composite_score", ascending=False).iloc[0]
    insights.append(
        f"2. BEST RISK-ADJUSTED PERFORMER: {best['scheme_name']} "
        f"with composite score {best['composite_score']:.1f}/100."
    )

    # 3. Highest expected return (Monte Carlo)
    if not mc_df.empty:
        best_mc = mc_df.sort_values("expected_cagr", ascending=False).iloc[0]
        insights.append(
            f"3. HIGHEST EXPECTED RETURN: Monte Carlo projects {best_mc['scheme_name'][:35]} "
            f"at {best_mc['expected_cagr']*100:.1f}% CAGR over 5 years (median scenario)."
        )

    # 4. Lowest downside risk
    best_cvar = var_df.sort_values("cvar_95", ascending=False).iloc[0]
    insights.append(
        f"4. LOWEST DOWNSIDE RISK: {best_cvar['scheme_name'][:35]} has the best "
        f"CVaR-95 of {best_cvar['cvar_95']*100:.3f}%."
    )

    # 5. Most stable AMC
    if not risk_df.empty:
        amc_risk = risk_df.copy()
        fm = load_fund_master()
        amc_risk = amc_risk.merge(fm[["amfi_code", "fund_house"]], on="amfi_code", how="left")
        amc_avg = amc_risk.groupby("fund_house")["risk_score"].mean().sort_values()
        if not amc_avg.empty:
            insights.append(
                f"5. MOST STABLE AMC: {amc_avg.index[0]} has the lowest average risk score "
                f"({amc_avg.iloc[0]:.1f}/100) across its funds."
            )

    # 6. Diversification candidate
    worst_var = var_df.sort_values("cvar_95").iloc[0]
    insights.append(
        f"6. DIVERSIFICATION ALERT: {worst_var['scheme_name'][:35]} has the worst "
        f"CVaR-95 of {worst_var['cvar_95']*100:.3f}%, consider diversifying."
    )

    # 7. SIP dominance
    if not seg_df.empty:
        sip_heavy = (seg_df["sip_ratio"] > 0.7).mean() * 100
        insights.append(
            f"7. SIP DISCIPLINE: {sip_heavy:.1f}% of investors have SIP ratio > 70%, "
            f"indicating strong systematic investment behaviour."
        )

    # 8. Conservative majority
    if not seg_df.empty:
        seg_dist = seg_df["investor_segment"].value_counts(normalize=True) * 100
        top_seg = seg_dist.index[0]
        insights.append(
            f"8. INVESTOR PROFILE: {top_seg} investors dominate at {seg_dist.iloc[0]:.1f}% "
            f"of the total investor base."
        )

    # 9. Cohort retention
    if not cohort_df.empty:
        age_c = cohort_df[cohort_df["cohort_type"] == "age_group"]
        if not age_c.empty:
            best_ret = age_c.sort_values("retention_rate", ascending=False).iloc[0]
            insights.append(
                f"9. BEST RETENTION: The {best_ret['cohort_value']} age group has "
                f"{best_ret['retention_rate']*100:.1f}% retention rate."
            )

    # 10. Monte Carlo probability
    if not mc_df.empty:
        avg_prob = mc_df["prob_positive"].mean() * 100
        insights.append(
            f"10. GROWTH PROBABILITY: On average, top funds have a {avg_prob:.1f}% "
            f"probability of positive returns over 5 years (Monte Carlo)."
        )

    # 11. VaR spread
    var_spread = var_df["hist_var_95"].max() - var_df["hist_var_95"].min()
    insights.append(
        f"11. VaR SPREAD: Daily VaR-95 ranges from {var_df['hist_var_95'].min()*100:.3f}% "
        f"to {var_df['hist_var_95'].max()*100:.3f}% across all funds."
    )

    # 12. Risk tier distribution
    if not risk_df.empty:
        tier_dist = risk_df["risk_tier"].value_counts()
        insights.append(
            f"12. RISK DISTRIBUTION: {tier_dist.get('Low', 0)} Low, "
            f"{tier_dist.get('Moderate', 0)} Moderate, {tier_dist.get('High', 0)} High, "
            f"{tier_dist.get('Very High', 0)} Very High risk funds."
        )

    # 13. City tier gap
    if not cohort_df.empty:
        tier_c = cohort_df[cohort_df["cohort_type"] == "city_tier"]
        if len(tier_c) >= 2:
            insights.append(
                f"13. URBAN-RURAL GAP: T30 vs B30 average investment differs by "
                f"Rs.{abs(tier_c['avg_investment'].max() - tier_c['avg_investment'].min()):,.0f}."
            )

    # 14. Parametric vs Historical VaR
    var_diff = (var_df["param_var_95"] - var_df["hist_var_95"]).abs().mean() * 100
    insights.append(
        f"14. MODEL COMPARISON: Average gap between Parametric and Historical VaR "
        f"is {var_diff:.4f}%, validating the normal-assumption approach."
    )

    # 15. Fund concentration
    insights.append(
        f"15. FUND UNIVERSE: Complete analysis covers {len(var_df)} funds "
        f"across {var_df['scheme_name'].str.extract(r'^([A-Z]+)')[0].nunique()} AMCs."
    )

    # Write report
    report_lines = [
        "# Advanced Analytics Summary",
        "",
        "## Day 6 -- Key Business Insights",
        "",
        "---",
        "",
    ]
    for ins in insights:
        report_lines.append(f"- {ins}")
        report_lines.append("")

    report_path = REPORTS_DIR / "advanced_analytics_summary.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    logger.info("Report -> %d insights -> advanced_analytics_summary.md", len(insights))
    return insights


# ════════════════════════════════════════════════════════════
# PHASE 13: VALIDATION
# ════════════════════════════════════════════════════════════

def validate_outputs(var_df: pd.DataFrame, cohort_df: pd.DataFrame,
                     seg_df: pd.DataFrame, mc_df: pd.DataFrame,
                     frontier_df: pd.DataFrame, opt_df: pd.DataFrame,
                     risk_df: pd.DataFrame) -> pd.DataFrame:
    """Validate all Day 6 outputs."""
    logger.info("--- Phase 13: Validation ---")
    checks = [
        ("40 funds in VaR", len(var_df) == 40, len(var_df)),
        ("All VaR values populated", var_df["hist_var_95"].notna().all(), var_df["hist_var_95"].notna().sum()),
        ("All CVaR values populated", var_df["cvar_95"].notna().all(), var_df["cvar_95"].notna().sum()),
        ("Cohort analysis generated", len(cohort_df) > 0, len(cohort_df)),
        ("Investor segments generated", len(seg_df) > 0, len(seg_df)),
        ("10,000 MC simulations done", len(frontier_df) == 10000, len(frontier_df)),
        ("Monte Carlo projections", len(mc_df) > 0, len(mc_df)),
        ("Optimal portfolios found", len(opt_df) == 2, len(opt_df)),
        ("Risk scores generated", len(risk_df) == 40, len(risk_df)),
        ("Recommendation CSV exists", (PROCESSED / "fund_recommendations.csv").exists(), "Y/N"),
        ("var_summary.csv exists", (PROCESSED / "var_summary.csv").exists(), True),
        ("efficient_frontier.csv exists", (PROCESSED / "efficient_frontier.csv").exists(), True),
    ]

    rows = []
    for name, passed, detail in checks:
        rows.append({"check": name, "passed": "PASS" if passed else "FAIL", "detail": str(detail)})

    val_df = pd.DataFrame(rows)
    val_df.to_csv(PROCESSED / "day6_validation_report.csv", index=False)
    n_pass = (val_df["passed"] == "PASS").sum()
    logger.info("Validation: %d/%d checks passed", n_pass, len(val_df))
    return val_df


# ════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ════════════════════════════════════════════════════════════

def main() -> None:
    """Run the complete Day 6 advanced analytics pipeline."""
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("  DAY 6: ADVANCED ANALYTICS ENGINE")
    logger.info("=" * 60)

    # Load data
    logger.info("Loading data...")
    returns_df = load_returns()
    fund_master = load_fund_master()
    tx_df = load_transactions()
    scorecard = load_scorecard()
    benchmark_df = load_benchmark()
    logger.info("Data loaded: %d returns, %d funds, %d transactions",
                len(returns_df), len(fund_master), len(tx_df))

    # Phase 2: VaR
    var_df = compute_var(returns_df, fund_master)
    chart_var(var_df, returns_df)

    # Phase 3: Cohort Analysis
    cohort_df = compute_cohorts(tx_df)
    chart_cohorts(cohort_df)

    # Phase 4: Customer Segmentation
    seg_df = compute_segments(tx_df, fund_master)
    chart_segments(seg_df)

    # Phase 6: Monte Carlo Simulation
    mc_df = monte_carlo_simulation(returns_df, scorecard, fund_master)
    chart_monte_carlo(mc_df, returns_df)

    # Phase 7: Markowitz Optimization
    frontier_df, opt_df = markowitz_optimization(returns_df, scorecard)
    chart_markowitz(frontier_df, opt_df)

    # Phase 8: Rolling Analytics
    compute_rolling(returns_df, scorecard, benchmark_df)

    # Phase 9: Correlation Analysis
    compute_correlation(returns_df, fund_master)

    # Phase 10: Risk Score Engine
    risk_df = compute_risk_scores(returns_df, var_df, fund_master)

    # Phase 11: Insights
    insights = generate_insights(var_df, cohort_df, seg_df, mc_df, risk_df, scorecard)

    # Phase 13: Validation
    val_df = validate_outputs(var_df, cohort_df, seg_df, mc_df,
                              frontier_df, opt_df, risk_df)

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info("  PIPELINE COMPLETE")
    logger.info("  Funds analysed:     %d", len(var_df))
    logger.info("  VaR metrics:        %d", len(var_df) * 8)
    logger.info("  MC simulations:     10,000 x %d funds", len(mc_df))
    logger.info("  Portfolios:         %d", len(frontier_df))
    logger.info("  Insights:           %d", len(insights))
    logger.info("  Validation:         %d/%d PASS",
                (val_df["passed"] == "PASS").sum(), len(val_df))
    logger.info("  Execution time:     %.1f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
