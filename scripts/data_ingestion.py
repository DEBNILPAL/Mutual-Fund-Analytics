"""
Bluestock MF Capstone — Day 1: Data Ingestion & Quality Profiling
=================================================================

This script performs automated data ingestion of all CSV datasets,
runs comprehensive quality profiling, fund master analysis,
and AMFI validation. All results are persisted to data/processed/.

Author : Bluestock Fintech Analytics Team
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

MISSING_THRESHOLD_PCT: float = 20.0  # flag columns with >20 % missing


# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
def _setup_logging() -> logging.Logger:
    """Configure file + console logging and return the root logger."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = LOG_DIR / "data_ingestion.log"

    logger = logging.getLogger("data_ingestion")
    logger.setLevel(logging.DEBUG)

    # File handler — detailed
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(funcName)-28s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Console handler — info+
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        logging.Formatter("%(levelname)-8s | %(message)s")
    )

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = _setup_logging()


# ---------------------------------------------------------------------------
# Phase 3 — Data Loading & Profiling
# ---------------------------------------------------------------------------
def load_dataset(filepath: Path) -> Optional[pd.DataFrame]:
    """
    Load a single CSV file into a DataFrame.

    Parameters
    ----------
    filepath : Path
        Absolute path to the CSV file.

    Returns
    -------
    pd.DataFrame or None
        Loaded DataFrame, or None on failure.
    """
    try:
        df: pd.DataFrame = pd.read_csv(filepath)
        logger.info(
            "Loaded %-40s | rows=%d | cols=%d",
            filepath.name, len(df), len(df.columns),
        )
        return df
    except Exception as exc:
        logger.error("Failed to load %s: %s", filepath.name, exc)
        return None


def profile_dataset(name: str, df: pd.DataFrame) -> dict:
    """
    Run automated quality profiling on a single DataFrame.

    Checks performed
    ----------------
    * Missing values (total & per-column)
    * Duplicate rows
    * Completely blank columns
    * Columns with >20 % missing
    * Potential datatype issues (object columns that look numeric)

    Parameters
    ----------
    name : str
        Human-readable dataset identifier.
    df : pd.DataFrame
        The DataFrame to profile.

    Returns
    -------
    dict
        Profile summary suitable for the quality report.
    """
    issues: list[str] = []

    # --- Missing values ---
    total_missing: int = int(df.isnull().sum().sum())
    if total_missing > 0:
        issues.append(f"Missing values: {total_missing}")
        high_missing_cols = [
            col for col in df.columns
            if df[col].isnull().mean() * 100 > MISSING_THRESHOLD_PCT
        ]
        if high_missing_cols:
            issues.append(f">20% missing: {high_missing_cols}")

    # --- Duplicate rows ---
    dup_count: int = int(df.duplicated().sum())
    if dup_count > 0:
        issues.append(f"Duplicate rows: {dup_count}")

    # --- Blank columns ---
    blank_cols: list[str] = [
        col for col in df.columns if df[col].isnull().all()
    ]
    if blank_cols:
        issues.append(f"Blank columns: {blank_cols}")

    # --- Potential datatype issues ---
    for col in df.select_dtypes(include=["object"]).columns:
        sample = df[col].dropna().head(50)
        numeric_like = sample.apply(
            lambda x: str(x).replace(".", "", 1).replace("-", "", 1).isdigit()
        )
        if numeric_like.mean() > 0.8:
            issues.append(f"Possible numeric stored as text: {col}")

    profile = {
        "dataset_name": name,
        "rows": len(df),
        "columns": len(df.columns),
        "missing_values": total_missing,
        "duplicates": dup_count,
        "blank_columns": len(blank_cols),
        "issues": "; ".join(issues) if issues else "None",
    }

    logger.debug("Profile for %s: %s", name, profile)
    return profile


def generate_quality_report(profiles: list[dict]) -> pd.DataFrame:
    """
    Compile individual profiles into a Data Quality Summary DataFrame
    and persist it to CSV.

    Parameters
    ----------
    profiles : list[dict]
        List of profile dicts from :func:`profile_dataset`.

    Returns
    -------
    pd.DataFrame
        The consolidated quality report.
    """
    try:
        report_df = pd.DataFrame(profiles)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_path: Path = PROCESSED_DIR / "data_quality_summary.csv"
        report_df.to_csv(out_path, index=False)
        logger.info("Data Quality Summary saved -> %s", out_path)
        return report_df
    except Exception as exc:
        logger.error("Failed to generate quality report: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Phase 4 — Fund Master Analysis
# ---------------------------------------------------------------------------
def analyze_fund_master(df: pd.DataFrame) -> pd.DataFrame:
    """
    Perform fund master profiling:
    * Unique fund houses, categories, sub-categories, risk categories
    * Schemes per AMC / category / risk category

    Parameters
    ----------
    df : pd.DataFrame
        01_fund_master dataset.

    Returns
    -------
    pd.DataFrame
        Schemes-per-AMC profile, also exported to CSV.
    """
    try:
        logger.info("=" * 60)
        logger.info("FUND MASTER ANALYSIS")
        logger.info("=" * 60)

        unique_fund_houses = df["fund_house"].nunique()
        unique_categories = df["category"].nunique()
        unique_sub_categories = df["sub_category"].nunique()
        unique_risk_categories = df["risk_category"].nunique()

        print("\n" + "=" * 60)
        print("  FUND MASTER PROFILE")
        print("=" * 60)
        print(f"  Unique Fund Houses       : {unique_fund_houses}")
        print(f"  Unique Categories        : {unique_categories}")
        print(f"  Unique Sub-Categories    : {unique_sub_categories}")
        print(f"  Unique Risk Categories   : {unique_risk_categories}")

        logger.info("Unique Fund Houses: %d", unique_fund_houses)
        logger.info("Unique Categories: %d", unique_categories)
        logger.info("Unique Sub-Categories: %d", unique_sub_categories)
        logger.info("Unique Risk Categories: %d", unique_risk_categories)

        schemes_per_amc = (
            df.groupby("fund_house")["scheme_name"]
            .count()
            .reset_index()
            .rename(columns={"scheme_name": "scheme_count"})
            .sort_values("scheme_count", ascending=False)
        )
        print("\n  Schemes per AMC:")
        for _, row in schemes_per_amc.iterrows():
            print(f"    {row['fund_house']:<35s} {row['scheme_count']:>3d}")

        schemes_per_category = (
            df.groupby("category")["scheme_name"]
            .count()
            .reset_index()
            .rename(columns={"scheme_name": "scheme_count"})
            .sort_values("scheme_count", ascending=False)
        )
        print("\n  Schemes per Category:")
        for _, row in schemes_per_category.iterrows():
            print(f"    {row['category']:<35s} {row['scheme_count']:>3d}")

        schemes_per_risk = (
            df.groupby("risk_category")["scheme_name"]
            .count()
            .reset_index()
            .rename(columns={"scheme_name": "scheme_count"})
            .sort_values("scheme_count", ascending=False)
        )
        print("\n  Schemes per Risk Category:")
        for _, row in schemes_per_risk.iterrows():
            print(f"    {row['risk_category']:<35s} {row['scheme_count']:>3d}")
        print("=" * 60)

        # Build combined profile
        profile_rows: list[dict] = []
        for _, row in schemes_per_amc.iterrows():
            profile_rows.append({
                "dimension": "fund_house",
                "value": row["fund_house"],
                "scheme_count": row["scheme_count"],
            })
        for _, row in schemes_per_category.iterrows():
            profile_rows.append({
                "dimension": "category",
                "value": row["category"],
                "scheme_count": row["scheme_count"],
            })
        for _, row in schemes_per_risk.iterrows():
            profile_rows.append({
                "dimension": "risk_category",
                "value": row["risk_category"],
                "scheme_count": row["scheme_count"],
            })

        profile_df = pd.DataFrame(profile_rows)
        out_path: Path = PROCESSED_DIR / "fund_master_profile.csv"
        profile_df.to_csv(out_path, index=False)
        logger.info("Fund Master Profile saved -> %s", out_path)
        return profile_df

    except Exception as exc:
        logger.error("Fund Master analysis failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Phase 5 — AMFI Validation
# ---------------------------------------------------------------------------
def validate_amfi_codes(
    fund_master_df: pd.DataFrame,
    nav_history_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cross-validate AMFI codes between fund_master and nav_history.

    Checks
    ------
    * Coverage percentage
    * Missing codes (in master but not in NAV)
    * Duplicate codes (repeated rows in master)
    * Invalid codes (in NAV but not in master)

    Parameters
    ----------
    fund_master_df : pd.DataFrame
    nav_history_df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        Validation results, also exported to CSV + TXT.
    """
    try:
        logger.info("=" * 60)
        logger.info("AMFI VALIDATION")
        logger.info("=" * 60)

        master_codes = set(fund_master_df["amfi_code"].unique())
        nav_codes = set(nav_history_df["amfi_code"].unique())

        matched = master_codes & nav_codes
        missing = master_codes - nav_codes
        invalid = nav_codes - master_codes
        dup_in_master = int(fund_master_df["amfi_code"].duplicated().sum())

        coverage_pct = (
            len(matched) / len(master_codes) * 100 if master_codes else 0.0
        )

        print("\n" + "=" * 60)
        print("  AMFI CODE VALIDATION")
        print("=" * 60)
        print(f"  Master codes          : {len(master_codes)}")
        print(f"  NAV history codes     : {len(nav_codes)}")
        print(f"  Matched               : {len(matched)}")
        print(f"  Coverage              : {coverage_pct:.2f}%")
        print(f"  Missing from NAV      : {len(missing)}  -> {sorted(missing) if missing else 'None'}")
        print(f"  Invalid in NAV        : {len(invalid)}  -> {sorted(invalid) if invalid else 'None'}")
        print(f"  Duplicate in master   : {dup_in_master}")
        print("=" * 60)

        logger.info("Coverage: %.2f%% | Missing: %d | Invalid: %d | Duplicates: %d",
                     coverage_pct, len(missing), len(invalid), dup_in_master)

        # --- Save CSV report ---
        report_rows: list[dict] = []
        for code in sorted(master_codes):
            status = "matched" if code in nav_codes else "missing_from_nav"
            report_rows.append({"amfi_code": code, "status": status})
        for code in sorted(invalid):
            report_rows.append({"amfi_code": code, "status": "invalid_in_nav"})

        report_df = pd.DataFrame(report_rows)
        csv_path: Path = PROCESSED_DIR / "amfi_validation_report.csv"
        report_df.to_csv(csv_path, index=False)
        logger.info("AMFI Validation CSV saved -> %s", csv_path)

        # --- Save TXT summary ---
        txt_path: Path = PROCESSED_DIR / "data_quality_summary.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("  BLUESTOCK MF CAPSTONE -- DATA QUALITY SUMMARY\n")
            f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

            f.write("AMFI CODE VALIDATION\n")
            f.write("-" * 40 + "\n")
            f.write(f"  Total master codes       : {len(master_codes)}\n")
            f.write(f"  Total NAV history codes   : {len(nav_codes)}\n")
            f.write(f"  Matched codes             : {len(matched)}\n")
            f.write(f"  Coverage                  : {coverage_pct:.2f}%\n")
            f.write(f"  Missing from NAV history  : {len(missing)}\n")
            if missing:
                f.write(f"    Codes: {sorted(missing)}\n")
            f.write(f"  Invalid codes in NAV      : {len(invalid)}\n")
            if invalid:
                f.write(f"    Codes: {sorted(invalid)}\n")
            f.write(f"  Duplicate codes in master : {dup_in_master}\n")
            f.write("\n")

            # Append per-dataset quality info
            quality_path = PROCESSED_DIR / "data_quality_summary.csv"
            if quality_path.exists():
                quality_df = pd.read_csv(quality_path)
                f.write("DATASET QUALITY OVERVIEW\n")
                f.write("-" * 40 + "\n")
                for _, row in quality_df.iterrows():
                    f.write(f"\n  Dataset     : {row['dataset_name']}\n")
                    f.write(f"  Rows        : {row['rows']}\n")
                    f.write(f"  Columns     : {row['columns']}\n")
                    f.write(f"  Missing     : {row['missing_values']}\n")
                    f.write(f"  Duplicates  : {row['duplicates']}\n")
                    f.write(f"  Blank Cols  : {row['blank_columns']}\n")
                    f.write(f"  Issues      : {row['issues']}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write("  END OF REPORT\n")
            f.write("=" * 70 + "\n")

        logger.info("Human-readable summary saved -> %s", txt_path)
        return report_df

    except Exception as exc:
        logger.error("AMFI validation failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """Orchestrate the full Day-1 data ingestion pipeline."""
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("BLUESTOCK MF CAPSTONE -- DATA INGESTION PIPELINE STARTED")
    logger.info("Timestamp: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Discover & load all CSVs
    # ------------------------------------------------------------------
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        logger.error("No CSV files found in %s", RAW_DIR)
        sys.exit(1)

    logger.info("Discovered %d CSV files in %s", len(csv_files), RAW_DIR)

    datasets: dict[str, pd.DataFrame] = {}
    for fp in csv_files:
        df = load_dataset(fp)
        if df is not None:
            datasets[fp.stem] = df

    # ------------------------------------------------------------------
    # Step 2: Print detailed info for each dataset
    # ------------------------------------------------------------------
    for name, df in datasets.items():
        print("\n" + "-" * 60)
        print(f"  DATASET : {name}")
        print("-" * 60)
        print(f"  Rows    : {df.shape[0]}")
        print(f"  Columns : {df.shape[1]}")
        print(f"  Shape   : {df.shape}")
        print(f"\n  Dtypes:\n{df.dtypes.to_string()}")
        print(f"\n  Head:\n{df.head().to_string()}")
        logger.info("Printed details for %s", name)

    # ------------------------------------------------------------------
    # Step 3: Profile each dataset
    # ------------------------------------------------------------------
    profiles: list[dict] = []
    for name, df in datasets.items():
        profile = profile_dataset(name, df)
        profiles.append(profile)

    quality_df = generate_quality_report(profiles)
    print("\n" + "=" * 60)
    print("  DATA QUALITY SUMMARY")
    print("=" * 60)
    print(quality_df.to_string(index=False))

    # ------------------------------------------------------------------
    # Step 4: Fund Master Analysis
    # ------------------------------------------------------------------
    fund_master_key = "01_fund_master"
    if fund_master_key in datasets:
        analyze_fund_master(datasets[fund_master_key])
    else:
        logger.warning("01_fund_master not found — skipping fund master analysis")

    # ------------------------------------------------------------------
    # Step 5: AMFI Validation
    # ------------------------------------------------------------------
    nav_key = "02_nav_history"
    if fund_master_key in datasets and nav_key in datasets:
        validate_amfi_codes(datasets[fund_master_key], datasets[nav_key])
    else:
        logger.warning("Required datasets for AMFI validation not found")

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETED in %.2f seconds", elapsed)
    logger.info("=" * 70)
    print(f"\n[OK] Pipeline completed in {elapsed:.2f}s")
    print(f"   Outputs -> {PROCESSED_DIR}")
    print(f"   Logs    -> {LOG_DIR / 'data_ingestion.log'}")


if __name__ == "__main__":
    main()
