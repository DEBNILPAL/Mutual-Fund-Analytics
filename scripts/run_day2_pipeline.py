"""
Bluestock MF Capstone -- Day 2: Pipeline Orchestrator
=====================================================

Runs the full Day 2 pipeline in sequence:
1. Data cleaning
2. SQLite warehouse loading
3. Row count validation
4. Validation report generation
5. Execution summary

Author : DEBNIL PAL
Date   : 2026-06-02
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
DB_DIR: Path = BASE_DIR / "data" / "db"
LOG_DIR: Path = BASE_DIR / "logs"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _setup_logging() -> logging.Logger:
    """Pipeline orchestrator logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = LOG_DIR / "day2_pipeline.log"

    logger = logging.getLogger("day2_pipeline")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
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
# Pipeline Steps
# ---------------------------------------------------------------------------

def step_1_cleaning() -> dict:
    """Run data cleaning pipeline."""
    logger.info("STEP 1: Data Cleaning")
    from data_cleaning import main as clean_main
    clean_main()
    # Read cleaning summary
    summary_path = PROCESSED_DIR / "cleaning_summary.csv"
    if summary_path.exists():
        return pd.read_csv(summary_path).to_dict("records")
    return []


def step_2_sqlite_load() -> pd.DataFrame:
    """Run SQLite loading pipeline."""
    logger.info("STEP 2: SQLite Loading")
    from load_to_sqlite import main as load_main
    verification = load_main()
    return verification


def step_3_validation(
    cleaning_records: list[dict],
    db_verification: pd.DataFrame,
) -> pd.DataFrame:
    """Generate day2_validation_report.csv."""
    logger.info("STEP 3: Validation Report")

    # Map dataset names to DB tables
    dataset_to_table = {
        "01_fund_master": "dim_fund",
        "02_nav_history": "fact_nav",
        "03_aum_by_fund_house": "fact_aum",
        "04_monthly_sip_inflows": "fact_sip_industry",
        "05_category_inflows": "fact_category_inflows",
        "06_industry_folio_count": "fact_industry_folios",
        "07_scheme_performance": "fact_performance",
        "08_investor_transactions": "fact_transactions",
        "09_portfolio_holdings": "fact_portfolio",
        "10_benchmark_indices": "fact_benchmark",
    }

    rows: list[dict] = []
    db_dict = {}
    if db_verification is not None:
        for _, row in db_verification.iterrows():
            db_dict[row["table"]] = int(row["actual_rows"])

    for rec in cleaning_records:
        ds_name = rec["dataset_name"]
        table = dataset_to_table.get(ds_name, "N/A")
        db_rows = db_dict.get(table, 0)

        # For NAV history, fact_nav rows != source rows (due to ffill expansion)
        # For transactions, rows match after invalid removal
        validation_status = "PASS"
        if table != "N/A" and db_rows <= 0:
            validation_status = "FAIL"

        rows.append({
            "dataset_name": ds_name,
            "source_rows": rec.get("source_rows", 0),
            "clean_rows": rec.get("clean_rows", 0),
            "db_rows": db_rows,
            "db_table": table,
            "duplicates_removed": rec.get("duplicates_removed", 0),
            "missing_values_fixed": rec.get("missing_values_fixed", 0),
            "invalid_removed": rec.get("invalid_removed", 0),
            "validation_status": validation_status,
        })

    report = pd.DataFrame(rows)
    out = PROCESSED_DIR / "day2_validation_report.csv"
    report.to_csv(out, index=False)
    logger.info("Validation report saved -> %s", out.name)
    return report


def step_4_summary(
    cleaning_records: list[dict],
    db_verification: pd.DataFrame,
    validation: pd.DataFrame,
    elapsed: float,
) -> None:
    """Print final execution summary."""

    print("\n" + "=" * 70)
    print("  DAY 2 PIPELINE -- FINAL EXECUTION SUMMARY")
    print("=" * 70)

    total_src = sum(r.get("source_rows", 0) for r in cleaning_records)
    total_clean = sum(r.get("clean_rows", 0) for r in cleaning_records)
    total_dups = sum(r.get("duplicates_removed", 0) for r in cleaning_records)
    total_missing = sum(r.get("missing_values_fixed", 0) for r in cleaning_records)
    total_invalid = sum(r.get("invalid_removed", 0) for r in cleaning_records)

    print(f"\n  Total source rows     : {total_src:,}")
    print(f"  Total clean rows      : {total_clean:,}")
    print(f"  Duplicates removed    : {total_dups:,}")
    print(f"  Missing values fixed  : {total_missing:,}")
    print(f"  Invalid removed       : {total_invalid:,}")

    print("\n  DATABASE TABLE COUNTS:")
    if db_verification is not None:
        for _, row in db_verification.iterrows():
            status_icon = "[OK]" if row["status"] == "PASS" else "[!!]"
            print(f"    {status_icon} {row['table']:<30s} {int(row['actual_rows']):>8,} rows")

    print(f"\n  Execution time : {elapsed:.2f}s")
    print(f"  Database       : {DB_DIR / 'bluestock_mf.db'}")
    print(f"  Cleaned CSVs   : {PROCESSED_DIR}")
    print(f"  Logs           : {LOG_DIR}")

    # Validation summary
    if validation is not None:
        pass_count = int((validation["validation_status"] == "PASS").sum())
        total = len(validation)
        print(f"\n  Validation     : {pass_count}/{total} PASS")

    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Orchestrate the full Day 2 pipeline."""
    start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("DAY 2 PIPELINE STARTED at %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 70)

    print("\n" + "#" * 70)
    print("  BLUESTOCK MF CAPSTONE -- DAY 2 PIPELINE")
    print("#" * 70)

    # Step 1: Cleaning
    cleaning_records = step_1_cleaning()

    # Step 2: SQLite Load
    db_verification = step_2_sqlite_load()

    # Step 3: Validation report
    validation = step_3_validation(cleaning_records, db_verification)

    print("\n" + "=" * 60)
    print("  VALIDATION REPORT")
    print("=" * 60)
    print(validation.to_string(index=False))

    # Step 4: Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    step_4_summary(cleaning_records, db_verification, validation, elapsed)

    logger.info("=" * 70)
    logger.info("DAY 2 PIPELINE COMPLETED in %.2f seconds", elapsed)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
