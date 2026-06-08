"""
Bluestock MF Dashboard -- Data Access Layer
============================================
All database queries are centralised here.
Every page imports data ONLY through these functions.
Uses @st.cache_data(ttl=600) for performance.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Database path ───────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = _BASE_DIR / "data" / "db" / "bluestock_mf.db"
PROCESSED_DIR = _BASE_DIR / "data" / "processed"

TTL = 600  # cache TTL in seconds


def _conn() -> sqlite3.Connection:
    """Return a new SQLite connection (thread-safe read-only)."""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def db_status() -> dict:
    """Return database health metadata."""
    try:
        conn = _conn()
        cur = conn.cursor()
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        total_rows = 0
        for (t,) in tables:
            total_rows += cur.execute(f"SELECT COUNT(1) FROM [{t}]").fetchone()[0]
        conn.close()
        return {
            "status": "Connected",
            "tables": len(tables),
            "total_rows": total_rows,
            "last_refresh": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        return {"status": f"Error: {e}", "tables": 0,
                "total_rows": 0, "last_refresh": "N/A"}


# ═══════════════════════════════════════════════════════════
# DIMENSION TABLES
# ═══════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL)
def get_fund_master() -> pd.DataFrame:
    """Load dim_fund."""
    return pd.read_sql("SELECT * FROM dim_fund", _conn())


# ═══════════════════════════════════════════════════════════
# FACT TABLES -- RAW
# ═══════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL)
def get_nav_data() -> pd.DataFrame:
    """Load fact_nav with parsed dates."""
    df = pd.read_sql("SELECT * FROM fact_nav", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df


@st.cache_data(ttl=TTL)
def get_aum_data() -> pd.DataFrame:
    """Load fact_aum."""
    df = pd.read_sql("SELECT * FROM fact_aum", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df


@st.cache_data(ttl=TTL)
def get_sip_data() -> pd.DataFrame:
    """Load fact_sip_industry."""
    df = pd.read_sql("SELECT * FROM fact_sip_industry", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df.sort_values("date")


@st.cache_data(ttl=TTL)
def get_transactions() -> pd.DataFrame:
    """Load fact_transactions."""
    df = pd.read_sql("SELECT * FROM fact_transactions", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df


@st.cache_data(ttl=TTL)
def get_benchmark_data() -> pd.DataFrame:
    """Load fact_benchmark."""
    df = pd.read_sql("SELECT * FROM fact_benchmark", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df.sort_values(["index_name", "date"])


@st.cache_data(ttl=TTL)
def get_portfolio_data() -> pd.DataFrame:
    """Load fact_portfolio."""
    return pd.read_sql("SELECT * FROM fact_portfolio", _conn())


@st.cache_data(ttl=TTL)
def get_category_inflows() -> pd.DataFrame:
    """Load fact_category_inflows."""
    df = pd.read_sql("SELECT * FROM fact_category_inflows", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df.sort_values("date")


@st.cache_data(ttl=TTL)
def get_industry_folios() -> pd.DataFrame:
    """Load fact_industry_folios."""
    df = pd.read_sql("SELECT * FROM fact_industry_folios", _conn())
    df["date"] = pd.to_datetime(df["date_id"])
    return df.sort_values("date")


@st.cache_data(ttl=TTL)
def get_performance_data() -> pd.DataFrame:
    """Load fact_performance."""
    return pd.read_sql("SELECT * FROM fact_performance", _conn())


# ═══════════════════════════════════════════════════════════
# PROCESSED / DAY-4 OUTPUTS
# ═══════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL)
def get_scorecard() -> pd.DataFrame:
    """Load fund_scorecard.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "fund_scorecard.csv")


@st.cache_data(ttl=TTL)
def get_sharpe() -> pd.DataFrame:
    """Load sharpe_values.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "sharpe_values.csv")


@st.cache_data(ttl=TTL)
def get_sortino() -> pd.DataFrame:
    """Load sortino_values.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "sortino_values.csv")


@st.cache_data(ttl=TTL)
def get_alpha_beta() -> pd.DataFrame:
    """Load alpha_beta.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "alpha_beta.csv")


@st.cache_data(ttl=TTL)
def get_cagr() -> pd.DataFrame:
    """Load cagr_report.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "cagr_report.csv")


@st.cache_data(ttl=TTL)
def get_max_drawdown() -> pd.DataFrame:
    """Load max_drawdown.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "max_drawdown.csv")


@st.cache_data(ttl=TTL)
def get_tracking_error() -> pd.DataFrame:
    """Load tracking_error.csv from Day 4."""
    return pd.read_csv(PROCESSED_DIR / "tracking_error.csv")


@st.cache_data(ttl=TTL)
def get_daily_returns() -> pd.DataFrame:
    """Load daily_returns.csv from Day 4 (large file -- sampled if needed)."""
    df = pd.read_csv(PROCESSED_DIR / "daily_returns.csv")
    df["date"] = pd.to_datetime(df["date_id"])
    return df
