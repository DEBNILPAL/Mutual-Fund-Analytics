"""
Bluestock MF Capstone -- Day 6: Fund Recommendation Engine
===========================================================
Author : DEBNIL PAL

Rule-based fund recommender that maps investor profiles
(Conservative / Balanced / Aggressive) to optimal fund picks
using a weighted scoring model across 7 risk-return factors.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ───────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"

logger = logging.getLogger("day6.recommender")

# ── Scoring Weights by Investor Type ────────────────────────
# Each weight reflects how much the investor values that factor.
# Positive = higher is better, Negative = lower is better.
WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "Conservative": {
        "sharpe_ratio":      0.20,
        "sortino_ratio":     0.15,
        "alpha_annual":      0.10,
        "beta_penalty":      0.20,   # lower beta preferred
        "expense_penalty":   0.15,   # lower expense preferred
        "drawdown_penalty":  0.15,   # lower drawdown preferred
        "risk_bonus":        0.05,   # bonus for low-risk category
    },
    "Balanced": {
        "sharpe_ratio":      0.25,
        "sortino_ratio":     0.15,
        "alpha_annual":      0.20,
        "beta_penalty":      0.10,
        "expense_penalty":   0.10,
        "drawdown_penalty":  0.10,
        "risk_bonus":        0.10,
    },
    "Aggressive": {
        "sharpe_ratio":      0.15,
        "sortino_ratio":     0.10,
        "alpha_annual":      0.30,
        "beta_penalty":      0.05,
        "expense_penalty":   0.05,
        "drawdown_penalty":  0.05,
        "risk_bonus":        0.30,
    },
}


def _load_fund_metrics() -> pd.DataFrame:
    """Merge scorecard with all Day 4 analytics outputs."""
    scorecard = pd.read_csv(PROCESSED / "fund_scorecard.csv")
    sharpe    = pd.read_csv(PROCESSED / "sharpe_values.csv")
    sortino   = pd.read_csv(PROCESSED / "sortino_values.csv")
    alpha_beta = pd.read_csv(PROCESSED / "alpha_beta.csv")
    drawdown  = pd.read_csv(PROCESSED / "max_drawdown.csv")

    merged = scorecard[["amfi_code", "scheme_name", "category",
                         "expense_ratio_pct", "composite_score", "tier"]].copy()
    merged = merged.merge(sharpe[["amfi_code", "sharpe_ratio"]], on="amfi_code", how="left")
    merged = merged.merge(sortino[["amfi_code", "sortino_ratio"]], on="amfi_code", how="left")
    merged = merged.merge(alpha_beta[["amfi_code", "alpha_annual", "beta"]], on="amfi_code", how="left")
    merged = merged.merge(drawdown[["amfi_code", "max_drawdown_pct"]], on="amfi_code", how="left")

    # Load risk category from dim_fund if available
    try:
        import sqlite3
        conn = sqlite3.connect(str(BASE_DIR / "data" / "db" / "bluestock_mf.db"))
        risk = pd.read_sql("SELECT amfi_code, risk_category FROM dim_fund", conn)
        conn.close()
        merged = merged.merge(risk, on="amfi_code", how="left")
    except Exception:
        merged["risk_category"] = "Moderate"

    return merged


def _normalise_col(series: pd.Series, invert: bool = False) -> pd.Series:
    """Min-max normalise to [0, 1]. If invert=True, lower raw = higher score."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    normed = (series - mn) / (mx - mn)
    return 1 - normed if invert else normed


def _risk_bonus_score(risk_category: pd.Series, investor_type: str) -> pd.Series:
    """Give bonus/penalty based on risk category alignment."""
    risk_map_aggressive  = {"Very High": 1.0, "High": 0.8, "Moderately High": 0.6,
                            "Moderate": 0.3, "Moderately Low": 0.1, "Low": 0.0}
    risk_map_conservative = {"Low": 1.0, "Moderately Low": 0.8, "Moderate": 0.6,
                             "Moderately High": 0.3, "High": 0.1, "Very High": 0.0}
    risk_map_balanced = {"Moderate": 1.0, "Moderately High": 0.7, "Moderately Low": 0.7,
                         "High": 0.4, "Low": 0.4, "Very High": 0.1}

    if investor_type == "Aggressive":
        return risk_category.map(risk_map_aggressive).fillna(0.5)
    elif investor_type == "Conservative":
        return risk_category.map(risk_map_conservative).fillna(0.5)
    else:
        return risk_category.map(risk_map_balanced).fillna(0.5)


def recommend_funds(top_n: int = 5) -> pd.DataFrame:
    """Generate top-N fund recommendations for each investor type."""
    logger.info("--- Phase 5: Fund Recommendation Engine ---")
    metrics = _load_fund_metrics()

    # Normalise all factors
    metrics["n_sharpe"]   = _normalise_col(metrics["sharpe_ratio"])
    metrics["n_sortino"]  = _normalise_col(metrics["sortino_ratio"])
    metrics["n_alpha"]    = _normalise_col(metrics["alpha_annual"])
    metrics["n_beta"]     = _normalise_col(metrics["beta"].abs(), invert=True)
    metrics["n_expense"]  = _normalise_col(metrics["expense_ratio_pct"], invert=True)
    metrics["n_drawdown"] = _normalise_col(metrics["max_drawdown_pct"].abs(), invert=True)

    all_recs = []
    for inv_type, weights in WEIGHT_PROFILES.items():
        df = metrics.copy()
        df["n_risk"] = _risk_bonus_score(df["risk_category"], inv_type)

        # Weighted composite score
        df["rec_score"] = (
            df["n_sharpe"]   * weights["sharpe_ratio"] +
            df["n_sortino"]  * weights["sortino_ratio"] +
            df["n_alpha"]    * weights["alpha_annual"] +
            df["n_beta"]     * weights["beta_penalty"] +
            df["n_expense"]  * weights["expense_penalty"] +
            df["n_drawdown"] * weights["drawdown_penalty"] +
            df["n_risk"]     * weights["risk_bonus"]
        )

        top = df.sort_values("rec_score", ascending=False).head(top_n)
        for rank, (_, row) in enumerate(top.iterrows(), 1):
            all_recs.append({
                "investor_type": inv_type,
                "rank": rank,
                "amfi_code": row["amfi_code"],
                "scheme_name": row["scheme_name"],
                "category": row["category"],
                "risk_category": row.get("risk_category", "N/A"),
                "sharpe_ratio": round(row["sharpe_ratio"], 3),
                "sortino_ratio": round(row["sortino_ratio"], 3),
                "alpha_annual": round(row["alpha_annual"], 4),
                "beta": round(row["beta"], 3),
                "expense_ratio_pct": round(row["expense_ratio_pct"], 2),
                "max_drawdown_pct": round(row["max_drawdown_pct"], 2),
                "recommendation_score": round(row["rec_score"], 4),
            })

    rec_df = pd.DataFrame(all_recs)
    rec_df.to_csv(PROCESSED / "fund_recommendations.csv", index=False)
    logger.info("Recommendations -> %d entries (3 types x %d each) -> fund_recommendations.csv",
                len(rec_df), top_n)

    for inv_type in WEIGHT_PROFILES:
        subset = rec_df[rec_df["investor_type"] == inv_type]
        logger.info("  %s -> Top pick: %s (score: %.3f)",
                    inv_type, subset.iloc[0]["scheme_name"][:35],
                    subset.iloc[0]["recommendation_score"])

    return rec_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-7s | %(message)s")
    recommend_funds()
