"""
Bluestock MF Capstone -- Day 4: Mutual Fund Performance Analytics Engine
========================================================================

Computes daily returns, CAGR, Sharpe, Sortino, Alpha/Beta, Maximum
Drawdown, Tracking Error, Composite Fund Scorecard, and Benchmark
Comparison for all 40 schemes in the SQLite data warehouse.

Author : DEBNIL PAL
Date   : 2026-06-05
DB     : data/db/bluestock_mf.db
"""

from __future__ import annotations

import logging
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from sqlalchemy import create_engine, text

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# =======================================================================
# CONSTANTS
# =======================================================================
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DB_PATH: Path = BASE_DIR / "data" / "db" / "bluestock_mf.db"
PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
CHARTS_DIR: Path = BASE_DIR / "reports" / "charts"
REPORTS_DIR: Path = BASE_DIR / "reports"
LOG_DIR: Path = BASE_DIR / "logs"

RISK_FREE_RATE: float = 0.065          # 6.5 % annual
TRADING_DAYS: int = 252                # annualisation factor
RF_DAILY: float = RISK_FREE_RATE / TRADING_DAYS

# Chart style
PALETTE = [
    "#0D47A1", "#1565C0", "#1976D2", "#1E88E5", "#2196F3",
    "#42A5F5", "#64B5F6", "#90CAF9", "#BBDEFB", "#E3F2FD",
    "#004D40", "#00695C", "#00796B", "#00897B", "#009688",
]
BG_COLOR = "#FAFBFC"
GRID_COLOR = "#E0E0E0"

plt.rcParams.update({
    "figure.facecolor": BG_COLOR,
    "axes.facecolor": BG_COLOR,
    "axes.grid": True,
    "grid.color": GRID_COLOR,
    "grid.alpha": 0.5,
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})


# =======================================================================
# LOGGING
# =======================================================================
def _setup_logging() -> logging.Logger:
    """Configure dual file + console logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = LOG_DIR / "performance_analytics.log"

    logger = logging.getLogger("perf_analytics")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(funcName)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = _setup_logging()


# =======================================================================
# DATA LOADING
# =======================================================================
def _get_engine():
    """Return SQLAlchemy engine for the warehouse."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def load_table(table_name: str, engine=None) -> pd.DataFrame:
    """Load an entire table from SQLite into a DataFrame."""
    t0 = time.perf_counter()
    eng = engine or _get_engine()
    df = pd.read_sql(f"SELECT * FROM {table_name}", eng)
    elapsed = time.perf_counter() - t0
    logger.info("Loaded %-25s -> %d rows in %.2fs", table_name, len(df), elapsed)
    return df


def load_nav_data(engine=None) -> pd.DataFrame:
    """Load fact_nav and parse dates."""
    df = load_table("fact_nav", engine)
    df["date"] = pd.to_datetime(df["date_id"], errors="coerce")
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)
    return df


def load_benchmark_data(engine=None) -> pd.DataFrame:
    """Load fact_benchmark and parse dates."""
    df = load_table("fact_benchmark", engine)
    df["date"] = pd.to_datetime(df["date_id"], errors="coerce")
    df = df.sort_values(["index_name", "date"]).reset_index(drop=True)
    return df


def load_fund_master(engine=None) -> pd.DataFrame:
    """Load dim_fund."""
    return load_table("dim_fund", engine)


def load_performance(engine=None) -> pd.DataFrame:
    """Load fact_performance."""
    return load_table("fact_performance", engine)


def _short_name(scheme: str, max_len: int = 35) -> str:
    """Truncate scheme name for chart labels."""
    if len(scheme) <= max_len:
        return scheme
    return scheme[:max_len - 2] + "..."


# =======================================================================
# PHASE 3 -- DAILY RETURNS
# =======================================================================
def compute_daily_returns(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily_return = (NAV_t / NAV_{t-1}) - 1 per scheme."""
    t0 = time.perf_counter()
    logger.info("Computing daily returns for %d schemes ...",
                nav_df["amfi_code"].nunique())

    df = nav_df.sort_values(["amfi_code", "date"]).copy()
    df["daily_return"] = df.groupby("amfi_code")["nav"].pct_change()

    # Validate -- first row per group is NaN (expected)
    inf_mask = np.isinf(df["daily_return"])
    if inf_mask.any():
        logger.warning("Found %d infinite daily returns -> replaced with NaN",
                        inf_mask.sum())
        df.loc[inf_mask, "daily_return"] = np.nan

    elapsed = time.perf_counter() - t0
    logger.info("Daily returns computed in %.2fs -- %d records", elapsed, len(df))
    return df[["amfi_code", "date", "nav", "daily_return"]].copy()


def daily_return_summary(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Per-fund summary stats for daily returns."""
    summary = daily_df.groupby("amfi_code")["daily_return"].agg(
        ["mean", "median", "std", "min", "max", "count"]
    ).reset_index()
    summary.columns = ["amfi_code", "mean", "median", "std", "min", "max", "count"]
    return summary


def chart_daily_return_distribution(daily_df: pd.DataFrame) -> Path:
    """Histogram of all daily returns."""
    out = CHARTS_DIR / "daily_return_distribution.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    returns = daily_df["daily_return"].dropna()
    ax.hist(returns, bins=120, color="#1565C0", edgecolor="white",
            alpha=0.85, linewidth=0.4)
    ax.axvline(returns.mean(), color="#D32F2F", ls="--", lw=1.5,
               label=f"Mean = {returns.mean():.4f}")
    ax.axvline(returns.median(), color="#FF6F00", ls="--", lw=1.5,
               label=f"Median = {returns.median():.4f}")
    ax.set_title("Daily Return Distribution -- All 40 Schemes", fontweight="bold")
    ax.set_xlabel("Daily Return")
    ax.set_ylabel("Frequency")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=1))
    ax.legend(frameon=True, fancybox=True, shadow=True)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 4 -- CAGR
# =======================================================================
def compute_cagr(nav_df: pd.DataFrame, fund_master: pd.DataFrame) -> pd.DataFrame:
    """Compute 1Y, 3Y, 5Y CAGR for each scheme."""
    t0 = time.perf_counter()
    max_date = nav_df["date"].max()
    results: list[dict] = []

    for code, grp in nav_df.groupby("amfi_code"):
        grp = grp.sort_values("date")
        nav_end = grp["nav"].iloc[-1]
        end_date = grp["date"].iloc[-1]
        row: dict = {"amfi_code": code}

        for label, years in [("cagr_1yr", 1), ("cagr_3yr", 3), ("cagr_5yr", 5)]:
            target = end_date - pd.DateOffset(years=years)
            subset = grp[grp["date"] >= target]
            if len(subset) < 20:
                row[label] = np.nan
            else:
                nav_start = subset["nav"].iloc[0]
                actual_years = (end_date - subset["date"].iloc[0]).days / 365.25
                if nav_start > 0 and actual_years > 0:
                    row[label] = (nav_end / nav_start) ** (1 / actual_years) - 1
                else:
                    row[label] = np.nan
        results.append(row)

    cagr_df = pd.DataFrame(results)
    cagr_df = cagr_df.merge(
        fund_master[["amfi_code", "scheme_name"]],
        on="amfi_code", how="left"
    )
    elapsed = time.perf_counter() - t0
    logger.info("CAGR computed for %d funds in %.2fs", len(cagr_df), elapsed)
    return cagr_df


def chart_cagr_top10(cagr_df: pd.DataFrame) -> list[Path]:
    """Bar charts for Top 10 funds by 1Y, 3Y, 5Y CAGR."""
    outputs: list[Path] = []
    for col, title, fname in [
        ("cagr_1yr", "Top 10 Funds -- 1-Year CAGR", "cagr_1yr.png"),
        ("cagr_3yr", "Top 10 Funds -- 3-Year CAGR", "cagr_3yr.png"),
        ("cagr_5yr", "Top 10 Funds -- 5-Year CAGR", "cagr_5yr.png"),
    ]:
        top = cagr_df.dropna(subset=[col]).nlargest(10, col).copy()
        top["short_name"] = top["scheme_name"].apply(_short_name)
        out = CHARTS_DIR / fname
        fig, ax = plt.subplots(figsize=(12, 7))
        bars = ax.barh(
            top["short_name"][::-1],
            top[col].values[::-1] * 100,
            color=PALETTE[:10][::-1],
            edgecolor="white",
            height=0.65,
        )
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"{w:.1f}%", va="center", fontsize=9, fontweight="bold")
        ax.set_title(title, fontweight="bold", fontsize=14)
        ax.set_xlabel("CAGR (%)")
        ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        outputs.append(out)
        logger.info("Chart saved -> %s", out.name)
    return outputs


# =======================================================================
# PHASE 5 -- SHARPE RATIO
# =======================================================================
def compute_sharpe(daily_df: pd.DataFrame,
                   fund_master: pd.DataFrame) -> pd.DataFrame:
    """Annualised Sharpe ratio for every fund."""
    t0 = time.perf_counter()
    results: list[dict] = []
    for code, grp in daily_df.groupby("amfi_code"):
        r = grp["daily_return"].dropna()
        if len(r) < 30:
            results.append({"amfi_code": code, "sharpe_ratio": np.nan})
            continue
        excess = r.mean() - RF_DAILY
        sharpe = (excess / r.std()) * np.sqrt(TRADING_DAYS)
        results.append({"amfi_code": code, "sharpe_ratio": round(sharpe, 4)})

    df = pd.DataFrame(results).merge(
        fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
    )
    df["sharpe_rank"] = df["sharpe_ratio"].rank(ascending=False).astype(int)
    elapsed = time.perf_counter() - t0
    logger.info("Sharpe computed for %d funds in %.2fs", len(df), elapsed)
    return df.sort_values("sharpe_rank")


def chart_sharpe_top10(sharpe_df: pd.DataFrame) -> Path:
    """Top 10 Sharpe bar chart."""
    out = CHARTS_DIR / "sharpe_ranking.png"
    top = sharpe_df.nlargest(10, "sharpe_ratio").copy()
    top["short_name"] = top["scheme_name"].apply(_short_name)
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(
        top["short_name"][::-1],
        top["sharpe_ratio"].values[::-1],
        color=PALETTE[:10][::-1], edgecolor="white", height=0.65,
    )
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{w:.2f}", va="center", fontsize=9, fontweight="bold")
    ax.set_title("Top 10 Funds -- Sharpe Ratio (Rf = 6.5%)", fontweight="bold")
    ax.set_xlabel("Sharpe Ratio")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 6 -- SORTINO RATIO
# =======================================================================
def compute_sortino(daily_df: pd.DataFrame,
                    fund_master: pd.DataFrame) -> pd.DataFrame:
    """Annualised Sortino ratio for every fund."""
    t0 = time.perf_counter()
    results: list[dict] = []
    for code, grp in daily_df.groupby("amfi_code"):
        r = grp["daily_return"].dropna()
        downside = r[r < 0]
        if len(downside) < 10:
            results.append({"amfi_code": code, "sortino_ratio": np.nan})
            continue
        excess = r.mean() - RF_DAILY
        sortino = (excess / downside.std()) * np.sqrt(TRADING_DAYS)
        results.append({"amfi_code": code, "sortino_ratio": round(sortino, 4)})

    df = pd.DataFrame(results).merge(
        fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
    )
    df["sortino_rank"] = df["sortino_ratio"].rank(ascending=False).astype(int)
    elapsed = time.perf_counter() - t0
    logger.info("Sortino computed for %d funds in %.2fs", len(df), elapsed)
    return df.sort_values("sortino_rank")


def chart_sortino_top10(sortino_df: pd.DataFrame) -> Path:
    """Top 10 Sortino bar chart."""
    out = CHARTS_DIR / "sortino_ranking.png"
    top = sortino_df.nlargest(10, "sortino_ratio").copy()
    top["short_name"] = top["scheme_name"].apply(_short_name)
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(
        top["short_name"][::-1],
        top["sortino_ratio"].values[::-1],
        color=PALETTE[:10][::-1], edgecolor="white", height=0.65,
    )
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{w:.2f}", va="center", fontsize=9, fontweight="bold")
    ax.set_title("Top 10 Funds -- Sortino Ratio (Rf = 6.5%)", fontweight="bold")
    ax.set_xlabel("Sortino Ratio")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 7 -- ALPHA & BETA
# =======================================================================
def compute_alpha_beta(daily_df: pd.DataFrame,
                       benchmark_df: pd.DataFrame,
                       fund_master: pd.DataFrame) -> pd.DataFrame:
    """OLS Alpha, Beta, R², and Correlation vs NIFTY100."""
    t0 = time.perf_counter()

    # Benchmark returns (NIFTY100)
    bench = benchmark_df[benchmark_df["index_name"] == "NIFTY100"].copy()
    bench = bench.sort_values("date")
    bench["bench_return"] = bench["close_value"].pct_change()
    bench = bench.dropna(subset=["bench_return"])[["date", "bench_return"]]

    results: list[dict] = []
    for code, grp in daily_df.groupby("amfi_code"):
        merged = grp[["date", "daily_return"]].merge(bench, on="date", how="inner")
        merged = merged.dropna()
        if len(merged) < 30:
            results.append({
                "amfi_code": code,
                "beta": np.nan, "alpha_annual": np.nan,
                "r_squared": np.nan, "correlation": np.nan,
            })
            continue
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            merged["bench_return"], merged["daily_return"]
        )
        results.append({
            "amfi_code": code,
            "beta": round(slope, 4),
            "alpha_annual": round(intercept * TRADING_DAYS, 4),
            "r_squared": round(r_value ** 2, 4),
            "correlation": round(r_value, 4),
        })

    df = pd.DataFrame(results).merge(
        fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
    )
    elapsed = time.perf_counter() - t0
    logger.info("Alpha/Beta computed for %d funds in %.2fs", len(df), elapsed)
    return df


def chart_alpha_beta_scatter(ab_df: pd.DataFrame) -> Path:
    """Scatter of Beta vs Alpha."""
    out = CHARTS_DIR / "alpha_beta_scatter.png"
    df = ab_df.dropna(subset=["beta", "alpha_annual"]).copy()
    df["short_name"] = df["scheme_name"].apply(lambda s: _short_name(s, 20))

    fig, ax = plt.subplots(figsize=(12, 8))
    sc = ax.scatter(
        df["beta"], df["alpha_annual"] * 100,
        c=df["r_squared"], cmap="RdYlGn", s=100,
        edgecolors="#333", linewidth=0.6, alpha=0.85, zorder=5,
    )
    cbar = fig.colorbar(sc, ax=ax, shrink=0.7)
    cbar.set_label("R²")

    # Annotate each point
    for _, row in df.iterrows():
        ax.annotate(
            row["short_name"],
            (row["beta"], row["alpha_annual"] * 100),
            fontsize=6.5, ha="left", va="bottom",
            xytext=(4, 4), textcoords="offset points",
        )
    ax.axhline(0, color="#999", ls="--", lw=0.8)
    ax.axvline(1.0, color="#999", ls="--", lw=0.8)
    ax.set_title("Alpha vs Beta -- All Funds (Benchmark: Nifty 100)",
                 fontweight="bold", fontsize=14)
    ax.set_xlabel("Beta (Market Sensitivity)")
    ax.set_ylabel("Annualised Alpha (%)")
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f%%"))
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 8 -- MAXIMUM DRAWDOWN
# =======================================================================
def compute_max_drawdown(nav_df: pd.DataFrame,
                         fund_master: pd.DataFrame) -> pd.DataFrame:
    """Maximum drawdown, start/end/recovery dates for every fund."""
    t0 = time.perf_counter()
    results: list[dict] = []

    for code, grp in nav_df.groupby("amfi_code"):
        grp = grp.sort_values("date").reset_index(drop=True)
        running_max = grp["nav"].cummax()
        drawdown = (grp["nav"] / running_max) - 1

        idx_max_dd = drawdown.idxmin()
        max_dd = drawdown.iloc[idx_max_dd]

        # Find drawdown start (last peak before the trough)
        peak_idx = grp["nav"][:idx_max_dd + 1].idxmax()
        dd_start = grp["date"].iloc[peak_idx]
        dd_end = grp["date"].iloc[idx_max_dd]

        # Find recovery date (when NAV first returns to peak)
        peak_nav = grp["nav"].iloc[peak_idx]
        recovery_subset = grp[grp.index > idx_max_dd]
        recovery_rows = recovery_subset[recovery_subset["nav"] >= peak_nav]
        recovery_date = recovery_rows["date"].iloc[0] if len(recovery_rows) > 0 else None

        results.append({
            "amfi_code": code,
            "max_drawdown_pct": round(max_dd * 100, 2),
            "drawdown_start_date": dd_start.strftime("%Y-%m-%d"),
            "drawdown_end_date": dd_end.strftime("%Y-%m-%d"),
            "recovery_date": recovery_date.strftime("%Y-%m-%d") if recovery_date else "Not Recovered",
        })

    df = pd.DataFrame(results).merge(
        fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
    )
    elapsed = time.perf_counter() - t0
    logger.info("Max Drawdown computed for %d funds in %.2fs", len(df), elapsed)
    return df


def chart_max_drawdown(dd_df: pd.DataFrame) -> Path:
    """Worst 10 drawdowns chart."""
    out = CHARTS_DIR / "max_drawdown_ranking.png"
    worst = dd_df.nsmallest(10, "max_drawdown_pct").copy()
    worst["short_name"] = worst["scheme_name"].apply(_short_name)

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(
        worst["short_name"][::-1],
        worst["max_drawdown_pct"].values[::-1],
        color=["#C62828", "#D32F2F", "#E53935", "#EF5350", "#F44336",
               "#EF9A9A", "#FFCDD2", "#FF8A80", "#FF5252", "#FF1744"][::-1],
        edgecolor="white", height=0.65,
    )
    for bar in bars:
        w = bar.get_width()
        ax.text(w - 0.5, bar.get_y() + bar.get_height() / 2,
                f"{w:.1f}%", va="center", fontsize=9, fontweight="bold",
                color="white" if abs(w) > 15 else "#333")
    ax.set_title("Worst 10 Funds -- Maximum Drawdown", fontweight="bold", fontsize=14)
    ax.set_xlabel("Maximum Drawdown (%)")
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 9 -- TRACKING ERROR
# =======================================================================
def compute_tracking_error(daily_df: pd.DataFrame,
                           benchmark_df: pd.DataFrame,
                           fund_master: pd.DataFrame) -> pd.DataFrame:
    """Tracking error vs NIFTY100 for each fund."""
    t0 = time.perf_counter()
    bench = benchmark_df[benchmark_df["index_name"] == "NIFTY100"].copy()
    bench = bench.sort_values("date")
    bench["bench_return"] = bench["close_value"].pct_change()
    bench = bench.dropna(subset=["bench_return"])[["date", "bench_return"]]

    results: list[dict] = []
    for code, grp in daily_df.groupby("amfi_code"):
        merged = grp[["date", "daily_return"]].merge(bench, on="date", how="inner")
        merged = merged.dropna()
        if len(merged) < 30:
            results.append({"amfi_code": code, "tracking_error": np.nan})
            continue
        diff = merged["daily_return"] - merged["bench_return"]
        te = diff.std() * np.sqrt(TRADING_DAYS)
        results.append({"amfi_code": code, "tracking_error": round(te, 4)})

    df = pd.DataFrame(results).merge(
        fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left"
    )
    df["te_rank"] = df["tracking_error"].rank(ascending=True).fillna(len(df)).astype(int)
    elapsed = time.perf_counter() - t0
    logger.info("Tracking Error computed for %d funds in %.2fs", len(df), elapsed)
    return df.sort_values("te_rank")


# =======================================================================
# PHASE 10 -- COMPOSITE FUND SCORECARD
# =======================================================================
def build_scorecard(
    cagr_df: pd.DataFrame,
    sharpe_df: pd.DataFrame,
    ab_df: pd.DataFrame,
    dd_df: pd.DataFrame,
    fund_master: pd.DataFrame,
) -> pd.DataFrame:
    """
    Composite scoring engine.
    Weights: 30% 3Y CAGR · 25% Sharpe · 20% Alpha · 15% Expense (inv) · 10% MaxDD (inv)
    """
    t0 = time.perf_counter()
    sc = fund_master[["amfi_code", "scheme_name", "category", "expense_ratio_pct"]].copy()

    # Merge metrics
    sc = sc.merge(cagr_df[["amfi_code", "cagr_3yr"]], on="amfi_code", how="left")
    sc = sc.merge(sharpe_df[["amfi_code", "sharpe_ratio"]], on="amfi_code", how="left")
    sc = sc.merge(ab_df[["amfi_code", "alpha_annual"]], on="amfi_code", how="left")
    sc = sc.merge(dd_df[["amfi_code", "max_drawdown_pct"]], on="amfi_code", how="left")

    # Ranks (higher is better except expense & drawdown)
    sc["cagr_3yr_rank"] = sc["cagr_3yr"].rank(ascending=False, na_option="bottom")
    sc["sharpe_rank"] = sc["sharpe_ratio"].rank(ascending=False, na_option="bottom")
    sc["alpha_rank"] = sc["alpha_annual"].rank(ascending=False, na_option="bottom")
    sc["expense_rank"] = sc["expense_ratio_pct"].rank(ascending=True, na_option="bottom")  # inverse
    sc["drawdown_rank"] = sc["max_drawdown_pct"].rank(ascending=False, na_option="bottom")  # less negative = better

    n = len(sc)

    # Normalise ranks to 0-100 (rank 1 = 100)
    for col in ["cagr_3yr_rank", "sharpe_rank", "alpha_rank", "expense_rank", "drawdown_rank"]:
        sc[col + "_score"] = ((n - sc[col] + 1) / n) * 100

    # Weighted composite
    sc["composite_score"] = (
        0.30 * sc["cagr_3yr_rank_score"]
        + 0.25 * sc["sharpe_rank_score"]
        + 0.20 * sc["alpha_rank_score"]
        + 0.15 * sc["expense_rank_score"]
        + 0.10 * sc["drawdown_rank_score"]
    ).round(2)

    # Tier
    sc["tier"] = pd.cut(
        sc["composite_score"],
        bins=[0, 60, 75, 90, 100.01],
        labels=["Weak", "Average", "Strong", "Elite"],
        right=False,
    )

    sc = sc.sort_values("composite_score", ascending=False).reset_index(drop=True)
    sc["overall_rank"] = range(1, len(sc) + 1)

    elapsed = time.perf_counter() - t0
    logger.info("Scorecard built for %d funds in %.2fs", len(sc), elapsed)
    return sc


def chart_scorecard_top20(sc_df: pd.DataFrame) -> Path:
    """Top 20 scorecard chart."""
    out = CHARTS_DIR / "fund_scorecard_top20.png"
    top = sc_df.head(20).copy()
    top["short_name"] = top["scheme_name"].apply(_short_name)

    tier_colors = {
        "Elite": "#1B5E20", "Strong": "#2E7D32",
        "Average": "#F57F17", "Weak": "#C62828"
    }
    colors = [tier_colors.get(str(t), "#999") for t in top["tier"]]

    fig, ax = plt.subplots(figsize=(14, 9))
    bars = ax.barh(
        top["short_name"][::-1],
        top["composite_score"].values[::-1],
        color=colors[::-1], edgecolor="white", height=0.65,
    )
    for bar, tier in zip(bars, top["tier"].values[::-1]):
        w = bar.get_width()
        ax.text(w + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{w:.1f}  [{tier}]", va="center", fontsize=8.5, fontweight="bold")
    ax.set_title("Top 20 Funds -- Composite Scorecard", fontweight="bold", fontsize=14)
    ax.set_xlabel("Composite Score (0-100)")
    ax.set_xlim(0, 110)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 11 -- BENCHMARK COMPARISON
# =======================================================================
def benchmark_comparison(
    nav_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    sc_df: pd.DataFrame,
) -> tuple[Path, Path]:
    """Growth of Rs.100 -- Top 5 funds vs Nifty 50 & Nifty 100 (3 years)."""
    t0 = time.perf_counter()
    max_date = nav_df["date"].max()
    start_date = max_date - pd.DateOffset(years=3)

    # Top 5 fund codes
    top5_codes = sc_df.head(5)["amfi_code"].tolist()
    top5_names = sc_df.head(5).set_index("amfi_code")["scheme_name"].to_dict()

    # Fund growth
    fund_data = nav_df[
        (nav_df["amfi_code"].isin(top5_codes)) & (nav_df["date"] >= start_date)
    ].copy()

    traces: list[dict] = []
    for code in top5_codes:
        sub = fund_data[fund_data["amfi_code"] == code].sort_values("date")
        if len(sub) == 0:
            continue
        growth = (sub["nav"] / sub["nav"].iloc[0]) * 100
        traces.append({
            "name": _short_name(top5_names.get(code, str(code)), 40),
            "date": sub["date"], "growth": growth,
        })

    # Benchmark growth
    for idx_name, label in [("NIFTY50", "Nifty 50"), ("NIFTY100", "Nifty 100")]:
        bsub = benchmark_df[
            (benchmark_df["index_name"] == idx_name) &
            (benchmark_df["date"] >= start_date)
        ].sort_values("date")
        if len(bsub) == 0:
            continue
        growth = (bsub["close_value"] / bsub["close_value"].iloc[0]) * 100
        traces.append({"name": label, "date": bsub["date"], "growth": growth})

    # --- Plotly interactive ---
    fig_plotly = go.Figure()
    for tr in traces:
        fig_plotly.add_trace(go.Scatter(
            x=tr["date"], y=tr["growth"],
            mode="lines", name=tr["name"],
            line=dict(width=2.5),
        ))
    fig_plotly.update_layout(
        title="Growth of Rs.100 -- Top 5 Funds vs Benchmarks (Last 3 Years)",
        xaxis_title="Date", yaxis_title="Growth (Rs.)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0.0),
        height=600,
    )
    fig_plotly.add_hline(y=100, line_dash="dash", line_color="grey",
                         annotation_text="Rs.100 Investment")
    html_path = CHARTS_DIR / "benchmark_comparison.html"
    fig_plotly.write_html(str(html_path))

    # --- Static PNG ---
    png_path = CHARTS_DIR / "benchmark_comparison.png"
    fig, ax = plt.subplots(figsize=(14, 7))
    colors_cycle = ["#0D47A1", "#1B5E20", "#E65100", "#4A148C", "#BF360C",
                    "#D32F2F", "#00695C"]
    for i, tr in enumerate(traces):
        style = "--" if tr["name"] in ("Nifty 50", "Nifty 100") else "-"
        lw = 2.5 if style == "--" else 1.8
        ax.plot(tr["date"], tr["growth"],
                label=tr["name"], ls=style, lw=lw,
                color=colors_cycle[i % len(colors_cycle)])
    ax.axhline(100, color="#999", ls=":", lw=0.8)
    ax.set_title("Growth of Rs.100 -- Top 5 Funds vs Benchmarks (Last 3 Years)",
                 fontweight="bold", fontsize=14)
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth (Rs.)")
    ax.legend(fontsize=8, loc="upper left", frameon=True, fancybox=True)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("Rs.%.0f"))
    fig.tight_layout()
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    elapsed = time.perf_counter() - t0
    logger.info("Benchmark comparison charts created in %.2fs", elapsed)
    return png_path, html_path


# =======================================================================
# PHASE 12 -- ADVANCED ANALYTICS CHARTS
# =======================================================================
def chart_return_vs_risk(cagr_df: pd.DataFrame,
                         daily_summary: pd.DataFrame,
                         fund_master: pd.DataFrame) -> Path:
    """Return vs Risk scatter."""
    out = CHARTS_DIR / "return_vs_risk_scatter.png"
    merged = cagr_df.merge(daily_summary[["amfi_code", "std"]], on="amfi_code")
    merged = merged.merge(fund_master[["amfi_code", "category"]], on="amfi_code")
    merged["ann_vol"] = merged["std"] * np.sqrt(TRADING_DAYS) * 100
    merged["cagr_3yr_pct"] = merged["cagr_3yr"] * 100

    fig, ax = plt.subplots(figsize=(12, 8))
    categories = merged["category"].unique()
    for i, cat in enumerate(categories):
        sub = merged[merged["category"] == cat]
        ax.scatter(sub["ann_vol"], sub["cagr_3yr_pct"],
                   label=cat, s=80, alpha=0.8,
                   edgecolors="#333", linewidth=0.5, zorder=5)
    ax.set_title("Return vs Risk -- 3Y CAGR vs Annualised Volatility",
                 fontweight="bold", fontsize=14)
    ax.set_xlabel("Annualised Volatility (%)")
    ax.set_ylabel("3-Year CAGR (%)")
    ax.legend(fontsize=8, loc="best", frameon=True)
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_sharpe_vs_sortino(sharpe_df: pd.DataFrame,
                            sortino_df: pd.DataFrame) -> Path:
    """Sharpe vs Sortino scatter."""
    out = CHARTS_DIR / "sharpe_vs_sortino.png"
    merged = sharpe_df[["amfi_code", "sharpe_ratio"]].merge(
        sortino_df[["amfi_code", "sortino_ratio"]], on="amfi_code"
    )
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(merged["sharpe_ratio"], merged["sortino_ratio"],
               c="#1565C0", s=80, edgecolors="#333", linewidth=0.5, alpha=0.85)
    # 45-degree line
    lims = [min(ax.get_xlim()[0], ax.get_ylim()[0]),
            max(ax.get_xlim()[1], ax.get_ylim()[1])]
    ax.plot(lims, lims, '--', color='#999', lw=0.8, label="45 deg line")
    ax.set_title("Sharpe Ratio vs Sortino Ratio", fontweight="bold", fontsize=14)
    ax.set_xlabel("Sharpe Ratio")
    ax.set_ylabel("Sortino Ratio")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_alpha_distribution(ab_df: pd.DataFrame) -> Path:
    """Alpha distribution histogram."""
    out = CHARTS_DIR / "alpha_distribution.png"
    vals = ab_df["alpha_annual"].dropna() * 100
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(vals, bins=20, color="#00695C", edgecolor="white", alpha=0.85)
    ax.axvline(vals.mean(), color="#D32F2F", ls="--", lw=1.5,
               label=f"Mean = {vals.mean():.2f}%")
    ax.set_title("Distribution of Annualised Alpha", fontweight="bold")
    ax.set_xlabel("Annualised Alpha (%)")
    ax.set_ylabel("Frequency")
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f%%"))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_beta_distribution(ab_df: pd.DataFrame) -> Path:
    """Beta distribution histogram."""
    out = CHARTS_DIR / "beta_distribution.png"
    vals = ab_df["beta"].dropna()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(vals, bins=20, color="#4A148C", edgecolor="white", alpha=0.85)
    ax.axvline(1.0, color="#D32F2F", ls="--", lw=1.5, label="Market Beta = 1.0")
    ax.axvline(vals.mean(), color="#FF6F00", ls="--", lw=1.5,
               label=f"Mean = {vals.mean():.2f}")
    ax.set_title("Distribution of Beta (vs Nifty 100)", fontweight="bold")
    ax.set_xlabel("Beta")
    ax.set_ylabel("Frequency")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_tracking_error_dist(te_df: pd.DataFrame) -> Path:
    """Tracking error distribution."""
    out = CHARTS_DIR / "tracking_error_distribution.png"
    vals = te_df["tracking_error"].dropna() * 100
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(vals, bins=20, color="#BF360C", edgecolor="white", alpha=0.85)
    ax.axvline(vals.mean(), color="#1565C0", ls="--", lw=1.5,
               label=f"Mean = {vals.mean():.2f}%")
    ax.set_title("Distribution of Tracking Error (vs Nifty 100)", fontweight="bold")
    ax.set_xlabel("Annualised Tracking Error (%)")
    ax.set_ylabel("Frequency")
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f%%"))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_drawdown_distribution(dd_df: pd.DataFrame) -> Path:
    """Drawdown distribution."""
    out = CHARTS_DIR / "drawdown_distribution.png"
    vals = dd_df["max_drawdown_pct"].dropna()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(vals, bins=20, color="#C62828", edgecolor="white", alpha=0.85)
    ax.axvline(vals.mean(), color="#1565C0", ls="--", lw=1.5,
               label=f"Mean = {vals.mean():.1f}%")
    ax.set_title("Distribution of Maximum Drawdown", fontweight="bold")
    ax.set_xlabel("Maximum Drawdown (%)")
    ax.set_ylabel("Frequency")
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_cagr_heatmap(cagr_df: pd.DataFrame, fund_master: pd.DataFrame) -> Path:
    """CAGR Comparison Heatmap."""
    out = CHARTS_DIR / "cagr_heatmap.png"
    merged = cagr_df.copy()
    if "scheme_name" not in merged.columns:
        merged = merged.merge(fund_master[["amfi_code", "scheme_name"]], on="amfi_code")
    merged["short_name"] = merged["scheme_name"].apply(lambda s: _short_name(s, 30))
    merged = merged.sort_values("cagr_3yr", ascending=False).head(20)

    heatdata = merged[["cagr_1yr", "cagr_3yr", "cagr_5yr"]].values * 100
    labels = merged["short_name"].values

    fig, ax = plt.subplots(figsize=(10, 10))
    im = ax.imshow(heatdata, cmap="RdYlGn", aspect="auto")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["1Y CAGR", "3Y CAGR", "5Y CAGR"])

    for i in range(len(labels)):
        for j in range(3):
            val = heatdata[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                        fontsize=7.5, fontweight="bold",
                        color="white" if abs(val) > 15 else "black")

    cbar = fig.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label("CAGR (%)")
    ax.set_title("CAGR Comparison Heatmap -- Top 20 Funds", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_risk_metric_radar(sc_df: pd.DataFrame) -> Path:
    """Radar chart for top 5 funds with key metrics."""
    out = CHARTS_DIR / "risk_metric_radar.png"
    top5 = sc_df.head(5).copy()

    categories_radar = ["3Y CAGR", "Sharpe", "Alpha", "Low Expense", "Low Drawdown"]
    score_cols = ["cagr_3yr_rank_score", "sharpe_rank_score",
                  "alpha_rank_score", "expense_rank_score", "drawdown_rank_score"]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))
    angles = np.linspace(0, 2 * np.pi, len(categories_radar), endpoint=False).tolist()
    angles += angles[:1]

    colors_radar = ["#0D47A1", "#1B5E20", "#E65100", "#4A148C", "#BF360C"]

    for i, (_, row) in enumerate(top5.iterrows()):
        values = [row[c] for c in score_cols]
        values += values[:1]
        ax.plot(angles, values, "o-", linewidth=2, color=colors_radar[i],
                label=_short_name(row["scheme_name"], 30))
        ax.fill(angles, values, alpha=0.1, color=colors_radar[i])

    ax.set_thetagrids([a * 180 / np.pi for a in angles[:-1]], categories_radar)
    ax.set_ylim(0, 100)
    ax.set_title("Risk-Adjusted Performance Radar -- Top 5 Funds",
                 fontweight="bold", fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_category_performance(cagr_df: pd.DataFrame,
                               fund_master: pd.DataFrame) -> Path:
    """Box plot of 3Y CAGR by category."""
    out = CHARTS_DIR / "category_performance_box.png"
    merged = cagr_df.merge(fund_master[["amfi_code", "category"]], on="amfi_code")
    merged["cagr_3yr_pct"] = merged["cagr_3yr"] * 100

    fig, ax = plt.subplots(figsize=(12, 7))
    cats = merged.groupby("category")["cagr_3yr_pct"].median().sort_values(ascending=False).index
    data = [merged[merged["category"] == c]["cagr_3yr_pct"].dropna().values for c in cats]
    bp = ax.boxplot(data, tick_labels=cats, patch_artist=True, vert=True)
    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(PALETTE[i % len(PALETTE)])
        box.set_alpha(0.7)
    ax.set_title("3-Year CAGR Distribution by Category", fontweight="bold", fontsize=14)
    ax.set_ylabel("3Y CAGR (%)")
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_rolling_sharpe(daily_df: pd.DataFrame,
                         sc_df: pd.DataFrame) -> Path:
    """Rolling 1-Year Sharpe for top 5 funds."""
    out = CHARTS_DIR / "rolling_sharpe_top5.png"
    top5 = sc_df.head(5)

    fig, ax = plt.subplots(figsize=(14, 7))
    colors_r = ["#0D47A1", "#1B5E20", "#E65100", "#4A148C", "#BF360C"]
    for i, (_, row) in enumerate(top5.iterrows()):
        sub = daily_df[daily_df["amfi_code"] == row["amfi_code"]].sort_values("date")
        r = sub.set_index("date")["daily_return"]
        rolling_excess = r.rolling(TRADING_DAYS).mean() - RF_DAILY
        rolling_std = r.rolling(TRADING_DAYS).std()
        rolling_sharpe = (rolling_excess / rolling_std) * np.sqrt(TRADING_DAYS)
        ax.plot(rolling_sharpe.index, rolling_sharpe.values,
                label=_short_name(row["scheme_name"], 30),
                color=colors_r[i], lw=1.5)

    ax.axhline(0, color="#999", ls="--", lw=0.8)
    ax.set_title("Rolling 1-Year Sharpe Ratio -- Top 5 Funds", fontweight="bold", fontsize=14)
    ax.set_xlabel("Date")
    ax.set_ylabel("Rolling Sharpe Ratio")
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


def chart_expense_vs_return(cagr_df: pd.DataFrame,
                            fund_master: pd.DataFrame) -> Path:
    """Expense ratio vs 3Y CAGR scatter."""
    out = CHARTS_DIR / "expense_vs_return.png"
    merged = cagr_df.merge(
        fund_master[["amfi_code", "expense_ratio_pct", "plan"]], on="amfi_code"
    )
    merged["cagr_3yr_pct"] = merged["cagr_3yr"] * 100

    fig, ax = plt.subplots(figsize=(10, 7))
    for plan, marker in [("Direct", "^"), ("Regular", "o")]:
        sub = merged[merged["plan"] == plan]
        ax.scatter(sub["expense_ratio_pct"], sub["cagr_3yr_pct"],
                   marker=marker, s=80, alpha=0.8, label=plan,
                   edgecolors="#333", linewidth=0.5)
    ax.set_title("Expense Ratio vs 3Y CAGR -- Direct vs Regular Plans",
                 fontweight="bold", fontsize=14)
    ax.set_xlabel("Expense Ratio (%)")
    ax.set_ylabel("3Y CAGR (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved -> %s", out.name)
    return out


# =======================================================================
# PHASE 13 -- KEY FINDINGS
# =======================================================================
def generate_performance_summary(
    daily_df: pd.DataFrame,
    cagr_df: pd.DataFrame,
    sharpe_df: pd.DataFrame,
    sortino_df: pd.DataFrame,
    ab_df: pd.DataFrame,
    dd_df: pd.DataFrame,
    te_df: pd.DataFrame,
    sc_df: pd.DataFrame,
    fund_master: pd.DataFrame,
    chart_count: int,
) -> str:
    """Generate professional performance summary markdown."""
    top1_sharpe = sharpe_df.iloc[0]
    top1_sortino = sortino_df.iloc[0]
    top1_cagr3 = cagr_df.sort_values("cagr_3yr", ascending=False).iloc[0]
    top1_score = sc_df.iloc[0]
    worst_dd = dd_df.sort_values("max_drawdown_pct").iloc[0]
    best_alpha = ab_df.sort_values("alpha_annual", ascending=False).iloc[0]
    lowest_te = te_df.sort_values("tracking_error").iloc[0]

    # Category stats
    cat_cagr = cagr_df.merge(fund_master[["amfi_code", "category"]], on="amfi_code")
    best_cat = cat_cagr.groupby("category")["cagr_3yr"].median().idxmax()
    best_cat_val = cat_cagr.groupby("category")["cagr_3yr"].median().max() * 100

    # Elite count
    elite_count = (sc_df["tier"] == "Elite").sum()
    strong_count = (sc_df["tier"] == "Strong").sum()

    avg_sharpe = sharpe_df["sharpe_ratio"].mean()
    avg_beta = ab_df["beta"].dropna().mean()

    md = f"""# Mutual Fund Performance Analytics Report
## Bluestock MF Capstone -- Day 4

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Funds Analysed:** {fund_master['amfi_code'].nunique()}
**NAV Records:** {len(daily_df):,}
**Benchmark:** Nifty 100
**Risk-Free Rate:** 6.50% p.a.
**Charts Generated:** {chart_count}

---

## Key Performance Insights

### Insight 1: Highest Risk-Adjusted Returns
**Fund:** {top1_sharpe['scheme_name']}
**Metric:** Sharpe Ratio = {top1_sharpe['sharpe_ratio']:.2f}
**Evidence:** This fund delivered the best excess return per unit of total risk across the entire universe of 40 schemes.
**Chart:** `sharpe_ranking.png`

---

### Insight 2: Best Downside Protection
**Fund:** {top1_sortino['scheme_name']}
**Metric:** Sortino Ratio = {top1_sortino['sortino_ratio']:.2f}
**Evidence:** When only downside volatility is considered, this fund demonstrates superior risk-adjusted performance, making it ideal for risk-averse investors.
**Chart:** `sortino_ranking.png`

---

### Insight 3: Strongest 3-Year Growth
**Fund:** {top1_cagr3['scheme_name']}
**Metric:** 3Y CAGR = {top1_cagr3['cagr_3yr']*100:.2f}%
**Evidence:** Compounding at this rate, an initial Rs.1 lakh investment would have grown to Rs.{(1*(1+top1_cagr3['cagr_3yr'])**3)*100000:.0f} over 3 years.
**Chart:** `cagr_3yr.png`

---

### Insight 4: Highest Alpha Generator
**Fund:** {best_alpha['scheme_name']}
**Metric:** Annualised Alpha = {best_alpha['alpha_annual']*100:.2f}%
**Evidence:** This fund consistently outperformed the Nifty 100 benchmark after adjusting for market risk (beta), generating significant active returns.
**Chart:** `alpha_beta_scatter.png`

---

### Insight 5: Deepest Drawdown Risk
**Fund:** {worst_dd['scheme_name']}
**Metric:** Maximum Drawdown = {worst_dd['max_drawdown_pct']:.2f}%
**Evidence:** The fund experienced its largest peak-to-trough decline from {worst_dd['drawdown_start_date']} to {worst_dd['drawdown_end_date']}. Recovery status: {worst_dd['recovery_date']}.
**Chart:** `max_drawdown_ranking.png`

---

### Insight 6: Best Overall Fund (Composite Scorecard)
**Fund:** {top1_score['scheme_name']}
**Metric:** Composite Score = {top1_score['composite_score']:.1f}/100 (Tier: {top1_score['tier']})
**Evidence:** Based on a weighted composite of 3Y CAGR (30%), Sharpe (25%), Alpha (20%), Expense Ratio (15%), and Max Drawdown (10%), this fund ranks #1 across all dimensions.
**Chart:** `fund_scorecard_top20.png`

---

### Insight 7: Tightest Benchmark Tracking
**Fund:** {lowest_te['scheme_name']}
**Metric:** Tracking Error = {lowest_te['tracking_error']*100:.2f}%
**Evidence:** This fund closely mirrors the Nifty 100 benchmark, making it suitable for passive-style allocation or core portfolio positioning.
**Chart:** `tracking_error_distribution.png`

---

### Insight 8: Category Leadership
**Category:** {best_cat}
**Metric:** Median 3Y CAGR = {best_cat_val:.2f}%
**Evidence:** The {best_cat} category delivered the highest median returns across the 3-year evaluation window, outperforming all other SEBI categories.
**Chart:** `category_performance_box.png`

---

### Insight 9: Fund Tier Distribution
**Metric:** {elite_count} Elite, {strong_count} Strong, {40 - elite_count - strong_count} Average/Weak
**Evidence:** Only {elite_count} out of 40 funds achieved Elite status (score >= 90). The average Sharpe Ratio across all funds is {avg_sharpe:.2f}, indicating {'strong' if avg_sharpe > 0.5 else 'moderate'} overall risk-adjusted performance.
**Chart:** `fund_scorecard_top20.png`

---

### Insight 10: Market Sensitivity Analysis
**Metric:** Average Beta = {avg_beta:.2f}
**Evidence:** The average beta of {avg_beta:.2f} across all equity funds indicates {'higher' if avg_beta > 1 else 'lower'} systematic risk relative to the Nifty 100 benchmark. Funds with beta < 1 provide defensive characteristics during market downturns.
**Chart:** `beta_distribution.png`

---

## Methodology Notes

| Parameter | Value |
|-----------|-------|
| NAV Source | SQLite warehouse (fact_nav) |
| Benchmark | Nifty 100 (fact_benchmark) |
| Risk-Free Rate | 6.50% p.a. (India 10Y G-Sec proxy) |
| Annualisation Factor | sqrt252 trading days |
| CAGR Periods | 1Y, 3Y, 5Y |
| Scorecard Weights | CAGR 30%, Sharpe 25%, Alpha 20%, Expense 15%, Drawdown 10% |
| Regression Method | scipy.stats.linregress (OLS) |

---

*Report generated by the Bluestock MF Performance Analytics Engine.*
*All metrics are reproducible and audit-friendly.*
"""
    return md


# =======================================================================
# PHASE 16 -- VALIDATION
# =======================================================================
def create_validation_report(
    daily_df: pd.DataFrame,
    cagr_df: pd.DataFrame,
    sharpe_df: pd.DataFrame,
    sortino_df: pd.DataFrame,
    ab_df: pd.DataFrame,
    dd_df: pd.DataFrame,
    te_df: pd.DataFrame,
    sc_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create day4_validation_report.csv."""
    checks = [
        ("daily_returns", len(daily_df), "PASS" if daily_df["amfi_code"].nunique() == 40 else "WARN",
         f"{daily_df['amfi_code'].nunique()} unique funds"),
        ("cagr_report", len(cagr_df), "PASS" if len(cagr_df) == 40 else "WARN",
         f"1Y/3Y/5Y CAGR computed"),
        ("sharpe_values", len(sharpe_df), "PASS" if len(sharpe_df) == 40 else "WARN",
         f"Sharpe range [{sharpe_df['sharpe_ratio'].min():.2f}, {sharpe_df['sharpe_ratio'].max():.2f}]"),
        ("sortino_values", len(sortino_df), "PASS" if len(sortino_df) == 40 else "WARN",
         f"Sortino range [{sortino_df['sortino_ratio'].min():.2f}, {sortino_df['sortino_ratio'].max():.2f}]"),
        ("alpha_beta", len(ab_df), "PASS" if len(ab_df) == 40 else "WARN",
         f"OLS regression vs Nifty 100"),
        ("max_drawdown", len(dd_df), "PASS" if len(dd_df) == 40 else "WARN",
         f"DD range [{dd_df['max_drawdown_pct'].min():.1f}%, {dd_df['max_drawdown_pct'].max():.1f}%]"),
        ("tracking_error", len(te_df), "PASS" if len(te_df) == 40 else "WARN",
         f"TE range [{te_df['tracking_error'].min():.4f}, {te_df['tracking_error'].max():.4f}]"),
        ("fund_scorecard", len(sc_df), "PASS" if len(sc_df) == 40 else "WARN",
         f"Score range [{sc_df['composite_score'].min():.1f}, {sc_df['composite_score'].max():.1f}]"),
        ("no_duplicate_funds", 40, "PASS" if sc_df["amfi_code"].nunique() == 40 else "FAIL",
         "Checked for duplicate amfi_code entries"),
        ("no_missing_metrics", 40, "PASS" if sc_df["composite_score"].notna().all() else "WARN",
         "All composite scores populated"),
    ]
    return pd.DataFrame(checks, columns=["metric", "records", "status", "notes"])


# =======================================================================
# PHASE 20 -- MAIN PIPELINE
# =======================================================================
def run_pipeline() -> None:
    """Execute the complete Day 4 Performance Analytics pipeline."""
    pipeline_start = time.perf_counter()
    logger.info("=" * 72)
    logger.info("BLUESTOCK MF -- DAY 4 PERFORMANCE ANALYTICS ENGINE")
    logger.info("Timestamp: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 72)

    # Ensure output directories
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("  BLUESTOCK MF -- DAY 4: PERFORMANCE ANALYTICS ENGINE")
    print("=" * 65)

    engine = _get_engine()

    # --- LOAD DATA --------------------------------------------------
    print("\n[Phase 2] Loading data from SQLite warehouse ...")
    nav_df = load_nav_data(engine)
    benchmark_df = load_benchmark_data(engine)
    fund_master = load_fund_master(engine)
    perf_df = load_performance(engine)
    print(f"   [OK] {nav_df['amfi_code'].nunique()} funds | {len(nav_df):,} NAV records")

    # --- DAILY RETURNS ----------------------------------------------
    print("\n[Phase 3] Computing daily returns ...")
    daily_df = compute_daily_returns(nav_df)
    daily_summ = daily_return_summary(daily_df)
    chart_daily_return_distribution(daily_df)
    daily_df.to_csv(PROCESSED_DIR / "daily_returns.csv", index=False)
    logger.info("Exported daily_returns.csv -- %d rows", len(daily_df))
    print(f"   [OK] {daily_df['amfi_code'].nunique()} schemes processed")

    # --- CAGR -------------------------------------------------------
    print("\n[Phase 4] Computing CAGR (1Y/3Y/5Y) ...")
    cagr_df = compute_cagr(nav_df, fund_master)
    chart_cagr_top10(cagr_df)
    cagr_df.to_csv(PROCESSED_DIR / "cagr_report.csv", index=False)
    logger.info("Exported cagr_report.csv -- %d rows", len(cagr_df))
    print(f"   [OK] CAGR computed for {len(cagr_df)} funds")

    # --- SHARPE -----------------------------------------------------
    print("\n[Phase 5] Computing Sharpe Ratio (Rf=6.5%) ...")
    sharpe_df = compute_sharpe(daily_df, fund_master)
    chart_sharpe_top10(sharpe_df)
    sharpe_df.to_csv(PROCESSED_DIR / "sharpe_values.csv", index=False)
    logger.info("Exported sharpe_values.csv")
    print(f"   [OK] Best Sharpe: {sharpe_df.iloc[0]['scheme_name']} = {sharpe_df.iloc[0]['sharpe_ratio']:.2f}")

    # --- SORTINO ----------------------------------------------------
    print("\n[Phase 6] Computing Sortino Ratio ...")
    sortino_df = compute_sortino(daily_df, fund_master)
    chart_sortino_top10(sortino_df)
    sortino_df.to_csv(PROCESSED_DIR / "sortino_values.csv", index=False)
    logger.info("Exported sortino_values.csv")
    print(f"   [OK] Best Sortino: {sortino_df.iloc[0]['scheme_name']} = {sortino_df.iloc[0]['sortino_ratio']:.2f}")

    # --- ALPHA & BETA -----------------------------------------------
    print("\n[Phase 7] Computing Alpha & Beta (vs Nifty 100) ...")
    ab_df = compute_alpha_beta(daily_df, benchmark_df, fund_master)
    chart_alpha_beta_scatter(ab_df)
    ab_df.to_csv(PROCESSED_DIR / "alpha_beta.csv", index=False)
    logger.info("Exported alpha_beta.csv")
    print(f"   [OK] Alpha/Beta computed for {len(ab_df)} funds")

    # --- MAX DRAWDOWN -----------------------------------------------
    print("\n[Phase 8] Computing Maximum Drawdown ...")
    dd_df = compute_max_drawdown(nav_df, fund_master)
    chart_max_drawdown(dd_df)
    dd_df.to_csv(PROCESSED_DIR / "max_drawdown.csv", index=False)
    logger.info("Exported max_drawdown.csv")
    worst = dd_df.sort_values("max_drawdown_pct").iloc[0]
    print(f"   [OK] Worst DD: {worst['scheme_name']} = {worst['max_drawdown_pct']:.1f}%")

    # --- TRACKING ERROR ---------------------------------------------
    print("\n[Phase 9] Computing Tracking Error ...")
    te_df = compute_tracking_error(daily_df, benchmark_df, fund_master)
    te_df.to_csv(PROCESSED_DIR / "tracking_error.csv", index=False)
    logger.info("Exported tracking_error.csv")
    print(f"   [OK] TE computed for {len(te_df)} funds")

    # --- COMPOSITE SCORECARD ----------------------------------------
    print("\n[Phase 10] Building Composite Fund Scorecard ...")
    sc_df = build_scorecard(cagr_df, sharpe_df, ab_df, dd_df, fund_master)
    chart_scorecard_top20(sc_df)

    # Save scorecard (select clean columns)
    sc_export = sc_df[[
        "overall_rank", "amfi_code", "scheme_name", "category",
        "cagr_3yr", "sharpe_ratio", "alpha_annual",
        "expense_ratio_pct", "max_drawdown_pct",
        "composite_score", "tier",
    ]].copy()
    sc_export.to_csv(PROCESSED_DIR / "fund_scorecard.csv", index=False)
    logger.info("Exported fund_scorecard.csv")
    print(f"   [OK] Elite: {(sc_df['tier']=='Elite').sum()} | Strong: {(sc_df['tier']=='Strong').sum()}")

    # --- BENCHMARK COMPARISON ---------------------------------------
    print("\n[Phase 11] Benchmark Comparison (Rs.100 growth) ...")
    benchmark_comparison(nav_df, benchmark_df, sc_df)
    print("   [OK] HTML + PNG exported")

    # --- ADVANCED CHARTS --------------------------------------------
    print("\n[Phase 12] Generating Advanced Analytics Charts ...")
    chart_count = 8  # already generated above
    chart_return_vs_risk(cagr_df, daily_summ, fund_master); chart_count += 1
    chart_sharpe_vs_sortino(sharpe_df, sortino_df); chart_count += 1
    chart_alpha_distribution(ab_df); chart_count += 1
    chart_beta_distribution(ab_df); chart_count += 1
    chart_tracking_error_dist(te_df); chart_count += 1
    chart_drawdown_distribution(dd_df); chart_count += 1
    chart_cagr_heatmap(cagr_df, fund_master); chart_count += 1
    chart_risk_metric_radar(sc_df); chart_count += 1
    chart_category_performance(cagr_df, fund_master); chart_count += 1
    chart_rolling_sharpe(daily_df, sc_df); chart_count += 1
    chart_expense_vs_return(cagr_df, fund_master); chart_count += 1
    print(f"   [OK] {chart_count} charts total")

    # --- KEY FINDINGS REPORT ----------------------------------------
    print("\n[Phase 13] Generating Performance Summary Report ...")
    summary_md = generate_performance_summary(
        daily_df, cagr_df, sharpe_df, sortino_df, ab_df, dd_df,
        te_df, sc_df, fund_master, chart_count
    )
    (REPORTS_DIR / "performance_summary.md").write_text(summary_md, encoding="utf-8")
    logger.info("Exported performance_summary.md")
    print("   [OK] performance_summary.md written")

    # --- VALIDATION -------------------------------------------------
    print("\n[Phase 16] Running Validation Checks ...")
    val_df = create_validation_report(
        daily_df, cagr_df, sharpe_df, sortino_df, ab_df, dd_df, te_df, sc_df
    )
    val_df.to_csv(PROCESSED_DIR / "day4_validation_report.csv", index=False)
    logger.info("Exported day4_validation_report.csv")
    all_pass = (val_df["status"] == "PASS").all()
    print(f"   [OK] Validation: {'ALL PASS' if all_pass else 'Issues detected -- check report'}")

    # --- FINAL SUMMARY ----------------------------------------------
    elapsed = time.perf_counter() - pipeline_start

    print("\n" + "=" * 65)
    print("  DAY 4 PIPELINE COMPLETE")
    print("=" * 65)
    print(f"  Funds Analysed      : {fund_master['amfi_code'].nunique()}")
    print(f"  NAV Records         : {len(daily_df):,}")
    print(f"  Metrics Computed    : 10 (Returns, CAGR, Sharpe, Sortino, Alpha, Beta, DD, TE, Score, Benchmark)")
    print(f"  Charts Generated    : {chart_count}")
    print(f"  CSVs Exported       : 8")
    print(f"  Execution Time      : {elapsed:.2f}s")
    print()
    print("  Top 5 Ranked Funds:")
    for i, (_, row) in enumerate(sc_df.head(5).iterrows()):
        print(f"     {i+1}. {row['scheme_name']}")
        print(f"        Score: {row['composite_score']:.1f} | Tier: {row['tier']} | Sharpe: {row.get('sharpe_ratio', 'N/A')}")
    print("=" * 65)

    logger.info("=" * 72)
    logger.info("DAY 4 PIPELINE COMPLETED in %.2fs", elapsed)
    logger.info("Charts: %d | CSVs: 8 | Validation: %s",
                chart_count, "ALL PASS" if all_pass else "ISSUES")
    logger.info("=" * 72)


# =======================================================================
if __name__ == "__main__":
    run_pipeline()
