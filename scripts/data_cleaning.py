"""
Bluestock MF Capstone -- Day 2: Data Cleaning & Validation
==========================================================

Cleans all 10 raw datasets with standardization, deduplication,
type casting, anomaly detection, and validation. Outputs cleaned
CSVs to data/processed/.

Author : DEBNIL PAL
Date   : 2026-06-02
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
RAW_DIR: Path = BASE_DIR / "data" / "raw"
PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
LOG_DIR: Path = BASE_DIR / "logs"

# Files that must NOT be touched (Day 1 API artifacts)
SKIP_FILES: set[str] = {
    "all_live_nav.csv",
    "nav_125497.csv", "nav_119551.csv", "nav_120503.csv",
    "nav_118632.csv", "nav_119092.csv", "nav_120841.csv",
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _setup_logging() -> logging.Logger:
    """Configure dual file + console logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = LOG_DIR / "data_cleaning.log"

    logger = logging.getLogger("data_cleaning")
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


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _trim_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all string columns."""
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()
    return df


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and underscore-ify column names."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9_]", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )
    return df


def _remove_duplicates(df: pd.DataFrame, name: str) -> tuple[pd.DataFrame, int]:
    """Drop exact duplicate rows and return (df, count_removed)."""
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        logger.info("%s: removed %d duplicate rows", name, removed)
    return df, removed


# ---------------------------------------------------------------------------
# Cleaning summary tracker
# ---------------------------------------------------------------------------
class CleaningSummary:
    """Accumulates per-dataset cleaning metrics."""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def add(
        self,
        dataset_name: str,
        source_rows: int,
        clean_rows: int,
        duplicates_removed: int = 0,
        missing_values_fixed: int = 0,
        invalid_removed: int = 0,
    ) -> None:
        self.records.append({
            "dataset_name": dataset_name,
            "source_rows": source_rows,
            "clean_rows": clean_rows,
            "duplicates_removed": duplicates_removed,
            "missing_values_fixed": missing_values_fixed,
            "invalid_removed": invalid_removed,
        })

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.records)


summary = CleaningSummary()


# ===========================================================================
# PHASE 6 -- SIMPLE DATASET CLEANERS
# ===========================================================================

def clean_fund_master() -> pd.DataFrame:
    """Clean 01_fund_master.csv."""
    name = "01_fund_master"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        # Parse launch_date
        df["launch_date"] = pd.to_datetime(df["launch_date"], errors="coerce")

        # Validate numeric fields
        for col in ["expense_ratio_pct", "exit_load_pct", "min_sip_amount", "min_lumpsum_amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Validate primary key
        pk_dups = int(df["amfi_code"].duplicated().sum())
        if pk_dups > 0:
            logger.warning("%s: %d duplicate amfi_code values", name, pk_dups)

        out = PROCESSED_DIR / f"clean_{name.split('_', 1)[1]}.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


def clean_aum_by_fund_house() -> pd.DataFrame:
    """Clean 03_aum_by_fund_house.csv."""
    name = "03_aum_by_fund_house"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["aum_lakh_crore", "aum_crore", "num_schemes"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        out = PROCESSED_DIR / "clean_aum_by_fund_house.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


def clean_monthly_sip_inflows() -> pd.DataFrame:
    """Clean 04_monthly_sip_inflows.csv -- handle missing yoy_growth_pct."""
    name = "04_monthly_sip_inflows"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        # Parse month -> date (first of month)
        df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")

        # Fix missing yoy_growth_pct
        missing_before = int(df["yoy_growth_pct"].isnull().sum())
        for col in ["sip_inflow_crore", "active_sip_accounts_crore",
                     "new_sip_accounts_lakh", "sip_aum_lakh_crore", "yoy_growth_pct"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # yoy_growth_pct is naturally missing for the first 12 months -- leave as NaN
        logger.info("%s: %d missing yoy_growth_pct values (expected for first year)",
                    name, missing_before)

        out = PROCESSED_DIR / "clean_monthly_sip_inflows.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups, missing_values_fixed=0)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


def clean_category_inflows() -> pd.DataFrame:
    """Clean 05_category_inflows.csv."""
    name = "05_category_inflows"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
        df["net_inflow_crore"] = pd.to_numeric(df["net_inflow_crore"], errors="coerce")

        out = PROCESSED_DIR / "clean_category_inflows.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


def clean_industry_folio_count() -> pd.DataFrame:
    """Clean 06_industry_folio_count.csv."""
    name = "06_industry_folio_count"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
        for col in ["total_folios_crore", "equity_folios_crore",
                     "debt_folios_crore", "hybrid_folios_crore", "others_folios_crore"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        out = PROCESSED_DIR / "clean_industry_folio_count.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


def clean_portfolio_holdings() -> pd.DataFrame:
    """Clean 09_portfolio_holdings.csv."""
    name = "09_portfolio_holdings"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="coerce")
        for col in ["weight_pct", "market_value_cr", "current_price_inr"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Validate weight_pct in valid range
        invalid_wt = int((df["weight_pct"] < 0).sum() + (df["weight_pct"] > 100).sum())
        if invalid_wt > 0:
            logger.warning("%s: %d holdings with invalid weight_pct", name, invalid_wt)

        out = PROCESSED_DIR / "clean_portfolio_holdings.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


def clean_benchmark_indices() -> pd.DataFrame:
    """Clean 10_benchmark_indices.csv."""
    name = "10_benchmark_indices"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["close_value"] = pd.to_numeric(df["close_value"], errors="coerce")
        df = df.sort_values(["index_name", "date"]).reset_index(drop=True)

        out = PROCESSED_DIR / "clean_benchmark_indices.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


# ===========================================================================
# PHASE 3 -- NAV HISTORY CLEANING
# ===========================================================================

def clean_nav_history() -> pd.DataFrame:
    """
    Clean 02_nav_history.csv with:
    - Date conversion, sorting, deduplication
    - NAV > 0 validation
    - Anomaly detection (daily return > +-50%)
    - Forward-fill missing business dates
    - Daily return computation
    """
    name = "02_nav_history"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)

        # 1. Convert date
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        # 2. Sort
        df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

        # 3. Remove duplicates (per amfi_code + date)
        before = len(df)
        df = df.drop_duplicates(subset=["amfi_code", "date"], keep="last")
        dups = before - len(df)
        if dups > 0:
            logger.info("%s: removed %d duplicate (amfi_code, date) pairs", name, dups)

        # 4. Validate NAV > 0
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        invalid_nav = int((df["nav"] <= 0).sum() + df["nav"].isnull().sum())
        df = df[df["nav"] > 0].reset_index(drop=True)
        if invalid_nav > 0:
            logger.warning("%s: removed %d rows with invalid NAV <= 0", name, invalid_nav)

        # 5. Detect anomalous NAV jumps
        df["prev_nav"] = df.groupby("amfi_code")["nav"].shift(1)
        df["daily_return_pct"] = ((df["nav"] / df["prev_nav"]) - 1) * 100
        df["nav_anomaly_flag"] = (
            (df["daily_return_pct"].abs() > 50) & df["daily_return_pct"].notna()
        ).astype(int)
        anomaly_count = int(df["nav_anomaly_flag"].sum())
        if anomaly_count > 0:
            logger.warning("%s: flagged %d anomalous NAV jumps (>50%%)", name, anomaly_count)

        # 6-8. Forward-fill missing business dates per scheme
        filled_count = 0
        frames: list[pd.DataFrame] = []
        all_dates = pd.bdate_range(df["date"].min(), df["date"].max())

        for code, grp in df.groupby("amfi_code"):
            grp = grp.set_index("date").reindex(all_dates)
            grp.index.name = "date"
            # Mark filled rows
            grp["nav_filled_flag"] = grp["nav"].isnull().astype(int)
            filled_in_scheme = int(grp["nav_filled_flag"].sum())
            filled_count += filled_in_scheme
            # Forward fill
            grp["nav"] = grp["nav"].ffill()
            grp["amfi_code"] = code
            # Recompute daily return after fill
            grp["daily_return_pct"] = ((grp["nav"] / grp["nav"].shift(1)) - 1) * 100
            grp["nav_anomaly_flag"] = grp["nav_anomaly_flag"].fillna(0).astype(int)
            frames.append(grp.reset_index())

        df = pd.concat(frames, ignore_index=True)
        df = df.rename(columns={"index": "date"})
        # Drop helper column
        if "prev_nav" in df.columns:
            df = df.drop(columns=["prev_nav"])

        # Drop rows still missing after ffill (start of series)
        df = df.dropna(subset=["nav"]).reset_index(drop=True)

        logger.info("%s: forward-filled %d missing business-day NAV values", name, filled_count)

        out = PROCESSED_DIR / "clean_nav_history.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups, filled_count)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


# ===========================================================================
# PHASE 4 -- INVESTOR TRANSACTIONS CLEANING
# ===========================================================================

def clean_investor_transactions() -> pd.DataFrame:
    """
    Clean 08_investor_transactions.csv with:
    - Standardize transaction_type, city_tier, kyc_status
    - Validate amount_inr > 0
    - High-value transaction flag (> 1M INR)
    - Invalid KYC flag
    """
    name = "08_investor_transactions"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        # Parse date
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

        # 1. Standardize transaction_type
        valid_tx = {"SIP", "Lumpsum", "Redemption"}
        df["transaction_type"] = df["transaction_type"].str.title()
        invalid_tx = int((~df["transaction_type"].isin(valid_tx)).sum()) if len(df) > 0 else 0
        # Map common misspellings
        tx_map = {"Sip": "SIP"}
        df["transaction_type"] = df["transaction_type"].replace(tx_map)

        # 2. Validate amount_inr > 0
        df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
        invalid_amt = int((df["amount_inr"] <= 0).sum() + df["amount_inr"].isnull().sum())
        df = df[df["amount_inr"] > 0].reset_index(drop=True)
        if invalid_amt > 0:
            logger.warning("%s: removed %d rows with invalid amount_inr", name, invalid_amt)

        # 3. Standardize state names
        df["state"] = df["state"].str.title()

        # 4. Validate city_tier
        valid_tiers = {"T30", "B30"}
        df["city_tier"] = df["city_tier"].str.upper()

        # 5. Validate kyc_status
        valid_kyc = {"Verified", "Pending"}
        df["kyc_status"] = df["kyc_status"].str.title()

        # 6. High-value transaction flag
        df["high_value_tx_flag"] = (df["amount_inr"] > 1_000_000).astype(int)
        hv_count = int(df["high_value_tx_flag"].sum())
        logger.info("%s: flagged %d high-value transactions (>1M INR)", name, hv_count)

        # 7. Invalid KYC flag (anything not Verified)
        df["invalid_kyc_flag"] = (~df["kyc_status"].isin({"Verified"})).astype(int)
        bad_kyc = int(df["invalid_kyc_flag"].sum())
        logger.info("%s: %d transactions with non-verified KYC", name, bad_kyc)

        # Validate gender
        df["gender"] = df["gender"].str.title()

        # Numeric columns
        df["annual_income_lakh"] = pd.to_numeric(df["annual_income_lakh"], errors="coerce")

        out = PROCESSED_DIR / "clean_investor_transactions.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups, invalid_removed=invalid_amt)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


# ===========================================================================
# PHASE 5 -- SCHEME PERFORMANCE CLEANING
# ===========================================================================

def clean_scheme_performance() -> pd.DataFrame:
    """
    Clean 07_scheme_performance.csv with anomaly flags:
    - sharpe_ratio < 0
    - beta > 3
    - return > 100%
    - expense_ratio outside 0.1-2.5
    """
    name = "07_scheme_performance"
    try:
        df = pd.read_csv(RAW_DIR / f"{name}.csv")
        src_rows = len(df)
        logger.info("Cleaning %s (%d rows)", name, src_rows)

        df = _standardize_columns(df)
        df = _trim_whitespace(df)
        df, dups = _remove_duplicates(df, name)

        # Cast numeric
        numeric_cols = [
            "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
            "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
            "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
            "aum_crore", "expense_ratio_pct", "morningstar_rating",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Anomaly flags
        df["flag_negative_sharpe"] = (df["sharpe_ratio"] < 0).astype(int)
        df["flag_high_beta"] = (df["beta"] > 3).astype(int)
        df["flag_extreme_return"] = (
            (df["return_1yr_pct"].abs() > 100) |
            (df["return_3yr_pct"].abs() > 100) |
            (df["return_5yr_pct"].abs() > 100)
        ).astype(int)
        df["flag_expense_ratio"] = (
            (df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)
        ).astype(int)

        # Log anomalies
        for flag_col in ["flag_negative_sharpe", "flag_high_beta",
                         "flag_extreme_return", "flag_expense_ratio"]:
            count = int(df[flag_col].sum())
            if count > 0:
                logger.warning("%s: %d rows flagged for %s", name, count, flag_col)

        out = PROCESSED_DIR / "clean_scheme_performance.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d rows)", out.name, len(df))

        summary.add(name, src_rows, len(df), dups)
        return df
    except Exception as exc:
        logger.error("Failed cleaning %s: %s", name, exc)
        raise


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> dict[str, pd.DataFrame]:
    """Run the full cleaning pipeline and return cleaned datasets."""
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("BLUESTOCK MF CAPSTONE -- DATA CLEANING PIPELINE STARTED")
    logger.info("Timestamp: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 70)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    datasets: dict[str, pd.DataFrame] = {}

    # Phase 6 -- simple datasets
    print("\n" + "=" * 60)
    print("  DATA CLEANING PIPELINE")
    print("=" * 60)

    datasets["fund_master"] = clean_fund_master()
    datasets["aum"] = clean_aum_by_fund_house()
    datasets["sip"] = clean_monthly_sip_inflows()
    datasets["category"] = clean_category_inflows()
    datasets["folio"] = clean_industry_folio_count()
    datasets["portfolio"] = clean_portfolio_holdings()
    datasets["benchmark"] = clean_benchmark_indices()

    # Phase 5 -- scheme performance
    datasets["performance"] = clean_scheme_performance()

    # Phase 4 -- investor transactions
    datasets["transactions"] = clean_investor_transactions()

    # Phase 3 -- NAV history (most complex)
    datasets["nav"] = clean_nav_history()

    # Save cleaning summary
    summary_df = summary.to_dataframe()
    summary_path = PROCESSED_DIR / "cleaning_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.info("Cleaning summary saved -> %s", summary_path.name)

    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("  CLEANING SUMMARY")
    print("=" * 60)
    print(summary_df.to_string(index=False))
    print(f"\n[OK] Cleaning completed in {elapsed:.2f}s")
    print(f"   Outputs -> {PROCESSED_DIR}")
    print(f"   Logs    -> {LOG_DIR / 'data_cleaning.log'}")

    logger.info("=" * 70)
    logger.info("CLEANING COMPLETED in %.2f seconds", elapsed)
    logger.info("=" * 70)

    return datasets


if __name__ == "__main__":
    main()
