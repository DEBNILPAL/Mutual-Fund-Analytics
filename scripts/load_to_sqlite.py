"""
Bluestock MF Capstone -- Day 2: SQLite Data Warehouse Loader
=============================================================

Reads cleaned CSVs, builds dim_date, and loads all tables into
data/db/bluestock_mf.db via SQLAlchemy. Verifies row counts.

Author : DEBNIL PAL
Date   : 2026-06-02
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
DB_DIR: Path = BASE_DIR / "data" / "db"
SQL_DIR: Path = BASE_DIR / "sql"
LOG_DIR: Path = BASE_DIR / "logs"

DB_PATH: Path = DB_DIR / "bluestock_mf.db"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _setup_logging() -> logging.Logger:
    """Configure dual file + console logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = LOG_DIR / "sqlite_load.log"

    logger = logging.getLogger("sqlite_load")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(funcName)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = _setup_logging()


# ---------------------------------------------------------------------------
# dim_date builder
# ---------------------------------------------------------------------------
def build_dim_date(engine: object, dates: pd.Series) -> int:
    """
    Build dim_date from all unique dates across datasets.

    Parameters
    ----------
    engine : SQLAlchemy engine
    dates : pd.Series of datetime

    Returns
    -------
    int : rows inserted
    """
    try:
        all_dates = pd.to_datetime(dates.dropna().unique())
        all_dates = pd.Series(all_dates).sort_values().reset_index(drop=True)

        dim = pd.DataFrame({
            "date_id": all_dates.dt.strftime("%Y-%m-%d"),
            "date": all_dates.dt.strftime("%Y-%m-%d"),
            "year": all_dates.dt.year,
            "quarter": all_dates.dt.quarter,
            "month": all_dates.dt.month,
            "month_name": all_dates.dt.month_name(),
            "week": all_dates.dt.isocalendar().week.astype(int),
            "day": all_dates.dt.day,
            "day_of_week": all_dates.dt.day_name(),
            "is_weekend": all_dates.dt.dayofweek.isin([5, 6]).astype(int),
        })

        dim = dim.drop_duplicates(subset=["date_id"])
        dim.to_sql("dim_date", engine, if_exists="replace", index=False)
        logger.info("dim_date: loaded %d date records", len(dim))
        return len(dim)
    except Exception as exc:
        logger.error("Failed building dim_date: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Table loaders
# ---------------------------------------------------------------------------
def _load_table(
    engine: object,
    table_name: str,
    df: pd.DataFrame,
    csv_name: str,
) -> int:
    """Load a DataFrame into a SQLite table and return row count."""
    try:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        logger.info("%-25s: loaded %d rows from %s", table_name, len(df), csv_name)
        return len(df)
    except Exception as exc:
        logger.error("Failed loading %s: %s", table_name, exc)
        raise


def load_dim_fund(engine: object) -> int:
    """Load dim_fund from clean_fund_master.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_fund_master.csv")
    return _load_table(engine, "dim_fund", df, "clean_fund_master.csv")


def load_fact_nav(engine: object) -> int:
    """Load fact_nav from clean_nav_history.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_nav_history.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date_id"] = df["date"].dt.strftime("%Y-%m-%d")
    cols = ["amfi_code", "date_id", "nav", "daily_return_pct",
            "nav_filled_flag", "nav_anomaly_flag"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_nav", df_out, "clean_nav_history.csv")


def load_fact_transactions(engine: object) -> int:
    """Load fact_transactions from clean_investor_transactions.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_investor_transactions.csv")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["date_id"] = df["transaction_date"].dt.strftime("%Y-%m-%d")
    cols = ["investor_id", "amfi_code", "date_id", "transaction_type",
            "amount_inr", "state", "city", "city_tier", "age_group",
            "gender", "annual_income_lakh", "payment_mode", "kyc_status",
            "high_value_tx_flag"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_transactions", df_out, "clean_investor_transactions.csv")


def load_fact_performance(engine: object) -> int:
    """Load fact_performance from clean_scheme_performance.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_scheme_performance.csv")
    cols = ["amfi_code", "scheme_name", "fund_house", "category", "plan",
            "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
            "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
            "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
            "aum_crore", "expense_ratio_pct", "morningstar_rating", "risk_grade"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_performance", df_out, "clean_scheme_performance.csv")


def load_fact_aum(engine: object) -> int:
    """Load fact_aum from clean_aum_by_fund_house.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_aum_by_fund_house.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date_id"] = df["date"].dt.strftime("%Y-%m-%d")
    cols = ["fund_house", "date_id", "aum_lakh_crore", "aum_crore", "num_schemes"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_aum", df_out, "clean_aum_by_fund_house.csv")


def load_fact_sip(engine: object) -> int:
    """Load fact_sip_industry from clean_monthly_sip_inflows.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_monthly_sip_inflows.csv")
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["date_id"] = df["month"].dt.strftime("%Y-%m-%d")
    cols = ["date_id", "sip_inflow_crore", "active_sip_accounts_crore",
            "new_sip_accounts_lakh", "sip_aum_lakh_crore", "yoy_growth_pct"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_sip_industry", df_out, "clean_monthly_sip_inflows.csv")


def load_fact_category_inflows(engine: object) -> int:
    """Load fact_category_inflows from clean_category_inflows.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_category_inflows.csv")
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["date_id"] = df["month"].dt.strftime("%Y-%m-%d")
    cols = ["date_id", "category", "net_inflow_crore"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_category_inflows", df_out, "clean_category_inflows.csv")


def load_fact_industry_folios(engine: object) -> int:
    """Load fact_industry_folios from clean_industry_folio_count.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_industry_folio_count.csv")
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["date_id"] = df["month"].dt.strftime("%Y-%m-%d")
    cols = ["date_id", "total_folios_crore", "equity_folios_crore",
            "debt_folios_crore", "hybrid_folios_crore", "others_folios_crore"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_industry_folios", df_out, "clean_industry_folio_count.csv")


def load_fact_portfolio(engine: object) -> int:
    """Load fact_portfolio from clean_portfolio_holdings.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_portfolio_holdings.csv")
    df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="coerce")
    df = df.rename(columns={"portfolio_date": "holding_date"})
    cols = ["amfi_code", "stock_symbol", "stock_name", "sector",
            "weight_pct", "market_value_cr", "current_price_inr", "holding_date"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_portfolio", df_out, "clean_portfolio_holdings.csv")


def load_fact_benchmark(engine: object) -> int:
    """Load fact_benchmark from clean_benchmark_indices.csv."""
    df = pd.read_csv(PROCESSED_DIR / "clean_benchmark_indices.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date_id"] = df["date"].dt.strftime("%Y-%m-%d")
    cols = ["date_id", "index_name", "close_value"]
    df_out = df[[c for c in cols if c in df.columns]].copy()
    return _load_table(engine, "fact_benchmark", df_out, "clean_benchmark_indices.csv")


# ---------------------------------------------------------------------------
# Schema executor
# ---------------------------------------------------------------------------
def execute_schema(engine: object) -> None:
    """Read and execute sql/schema.sql."""
    schema_path = SQL_DIR / "schema.sql"
    try:
        sql_text = schema_path.read_text(encoding="utf-8")
        with engine.connect() as conn:
            for statement in sql_text.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
            conn.commit()
        logger.info("Schema executed from %s", schema_path.name)
    except Exception as exc:
        logger.error("Failed executing schema: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Row count verification
# ---------------------------------------------------------------------------
def verify_row_counts(engine: object, expected: dict[str, int]) -> pd.DataFrame:
    """Compare expected vs actual row counts in each table."""
    rows: list[dict] = []
    with engine.connect() as conn:
        for table, exp in expected.items():
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                actual = result.scalar()
                status = "PASS" if actual == exp else "MISMATCH"
                rows.append({
                    "table": table,
                    "expected_rows": exp,
                    "actual_rows": actual,
                    "status": status,
                })
                if status == "MISMATCH":
                    logger.warning("Row mismatch: %s expected=%d actual=%d",
                                   table, exp, actual)
            except Exception as exc:
                rows.append({
                    "table": table,
                    "expected_rows": exp,
                    "actual_rows": -1,
                    "status": f"ERROR: {exc}",
                })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Collect all dates for dim_date
# ---------------------------------------------------------------------------
def collect_all_dates() -> pd.Series:
    """Gather unique dates from all cleaned datasets."""
    all_dates: list = []

    # NAV history dates
    nav = pd.read_csv(PROCESSED_DIR / "clean_nav_history.csv")
    all_dates.extend(pd.to_datetime(nav["date"], errors="coerce").dropna().tolist())

    # Transaction dates
    tx = pd.read_csv(PROCESSED_DIR / "clean_investor_transactions.csv")
    all_dates.extend(pd.to_datetime(tx["transaction_date"], errors="coerce").dropna().tolist())

    # AUM dates
    aum = pd.read_csv(PROCESSED_DIR / "clean_aum_by_fund_house.csv")
    all_dates.extend(pd.to_datetime(aum["date"], errors="coerce").dropna().tolist())

    # SIP dates
    sip = pd.read_csv(PROCESSED_DIR / "clean_monthly_sip_inflows.csv")
    all_dates.extend(pd.to_datetime(sip["month"], errors="coerce").dropna().tolist())

    # Category inflows
    cat = pd.read_csv(PROCESSED_DIR / "clean_category_inflows.csv")
    all_dates.extend(pd.to_datetime(cat["month"], errors="coerce").dropna().tolist())

    # Folio count
    fol = pd.read_csv(PROCESSED_DIR / "clean_industry_folio_count.csv")
    all_dates.extend(pd.to_datetime(fol["month"], errors="coerce").dropna().tolist())

    # Benchmark dates
    bench = pd.read_csv(PROCESSED_DIR / "clean_benchmark_indices.csv")
    all_dates.extend(pd.to_datetime(bench["date"], errors="coerce").dropna().tolist())

    # Portfolio dates
    port = pd.read_csv(PROCESSED_DIR / "clean_portfolio_holdings.csv")
    all_dates.extend(pd.to_datetime(port["portfolio_date"], errors="coerce").dropna().tolist())

    return pd.Series(all_dates)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> pd.DataFrame:
    """Orchestrate the full SQLite loading pipeline."""
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("BLUESTOCK MF CAPSTONE -- SQLITE LOAD STARTED")
    logger.info("Timestamp: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 70)

    DB_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old DB for clean load
    if DB_PATH.exists():
        DB_PATH.unlink()
        logger.info("Removed existing database: %s", DB_PATH.name)

    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

    print("\n" + "=" * 60)
    print("  SQLITE DATA WAREHOUSE LOADING")
    print("=" * 60)

    # Execute schema
    execute_schema(engine)

    # Build dim_date from all dates
    all_dates = collect_all_dates()
    dim_date_rows = build_dim_date(engine, all_dates)

    # Load all tables
    expected: dict[str, int] = {}

    expected["dim_fund"] = load_dim_fund(engine)
    expected["dim_date"] = dim_date_rows
    expected["fact_nav"] = load_fact_nav(engine)
    expected["fact_transactions"] = load_fact_transactions(engine)
    expected["fact_performance"] = load_fact_performance(engine)
    expected["fact_aum"] = load_fact_aum(engine)
    expected["fact_sip_industry"] = load_fact_sip(engine)
    expected["fact_category_inflows"] = load_fact_category_inflows(engine)
    expected["fact_industry_folios"] = load_fact_industry_folios(engine)
    expected["fact_portfolio"] = load_fact_portfolio(engine)
    expected["fact_benchmark"] = load_fact_benchmark(engine)

    # Create indexes (schema.sql has them, but ensure)
    with engine.connect() as conn:
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_nav_amfi ON fact_nav(amfi_code)",
            "CREATE INDEX IF NOT EXISTS idx_nav_date ON fact_nav(date_id)",
            "CREATE INDEX IF NOT EXISTS idx_tx_amfi ON fact_transactions(amfi_code)",
            "CREATE INDEX IF NOT EXISTS idx_tx_date ON fact_transactions(date_id)",
            "CREATE INDEX IF NOT EXISTS idx_perf_amfi ON fact_performance(amfi_code)",
            "CREATE INDEX IF NOT EXISTS idx_aum_date ON fact_aum(date_id)",
        ]:
            conn.execute(text(idx_sql))
        conn.commit()
    logger.info("Indexes created/verified")

    # Verify row counts
    verification = verify_row_counts(engine, expected)

    print("\n" + "=" * 60)
    print("  ROW COUNT VERIFICATION")
    print("=" * 60)
    print(verification.to_string(index=False))

    elapsed = (datetime.now() - start_time).total_seconds()
    all_pass = (verification["status"] == "PASS").all()

    print(f"\n[OK] SQLite load completed in {elapsed:.2f}s")
    print(f"   Database -> {DB_PATH}")
    print(f"   Status   -> {'ALL PASS' if all_pass else 'ISSUES DETECTED'}")

    logger.info("=" * 70)
    logger.info("SQLITE LOAD COMPLETED in %.2f seconds | Status: %s",
                elapsed, "ALL PASS" if all_pass else "ISSUES")
    logger.info("=" * 70)

    return verification


if __name__ == "__main__":
    main()
