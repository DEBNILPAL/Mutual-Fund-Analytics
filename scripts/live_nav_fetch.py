"""
Bluestock MF Capstone -- Day 1: Live NAV Fetch via MFAPI
========================================================

Fetches live NAV data for selected mutual fund schemes from the
public MFAPI (https://api.mfapi.in/mf/{amfi_code}).

Features
--------
* Graceful handling of connection failures, timeouts, and bad responses.
* Per-scheme CSV export + consolidated all_live_nav.csv.
* Professional logging to logs/nav_fetch.log.

Author : Bluestock Fintech Analytics Team
Date   : 2026-06-02
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
RAW_DIR: Path = BASE_DIR / "data" / "raw"
LOG_DIR: Path = BASE_DIR / "logs"

API_BASE_URL: str = "https://api.mfapi.in/mf"
REQUEST_TIMEOUT: int = 30  # seconds

# Schemes to fetch (Phase 7)
SCHEMES: dict[int, str] = {
    125497: "HDFC Top 100 Direct",
    119551: "SBI Bluechip",
    120503: "ICICI Bluechip",
    118632: "Nippon Large Cap",
    119092: "Axis Bluechip",
    120841: "Kotak Bluechip",
}


# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
def _setup_logging() -> logging.Logger:
    """Configure file + console logging for the NAV fetch module."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = LOG_DIR / "nav_fetch.log"

    logger = logging.getLogger("nav_fetch")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(funcName)-24s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = _setup_logging()


# ---------------------------------------------------------------------------
# Phase 6 -- NAV API Fetch
# ---------------------------------------------------------------------------
def fetch_nav(amfi_code: int) -> Optional[dict]:
    """
    Fetch NAV data for a single scheme from the MFAPI.

    Parameters
    ----------
    amfi_code : int
        The AMFI scheme code.

    Returns
    -------
    dict or None
        JSON response containing scheme metadata and NAV history,
        or None on failure.
    """
    url: str = f"{API_BASE_URL}/{amfi_code}"
    logger.info("Fetching NAV -> %s", url)

    try:
        start = time.time()
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        elapsed = time.time() - start

        logger.info(
            "Response: status=%d | time=%.2fs | size=%d bytes",
            response.status_code, elapsed, len(response.content),
        )

        if response.status_code != 200:
            logger.error(
                "Bad HTTP status %d for AMFI %d", response.status_code, amfi_code
            )
            return None

        data: dict = response.json()

        # Validate response structure
        if "data" not in data or not data["data"]:
            logger.warning("Empty NAV data returned for AMFI %d", amfi_code)
            return None

        logger.info(
            "NAV records received: %d for scheme '%s'",
            len(data["data"]),
            data.get("meta", {}).get("scheme_name", "Unknown"),
        )
        return data

    except requests.exceptions.Timeout:
        logger.error("Timeout after %ds for AMFI %d", REQUEST_TIMEOUT, amfi_code)
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error("Connection failed for AMFI %d: %s", amfi_code, exc)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Request error for AMFI %d: %s", amfi_code, exc)
        return None
    except ValueError as exc:
        logger.error("JSON decode error for AMFI %d: %s", amfi_code, exc)
        return None


# ---------------------------------------------------------------------------
# Phase 7 -- Batch Download & Export
# ---------------------------------------------------------------------------
def download_and_export(schemes: dict[int, str]) -> pd.DataFrame:
    """
    Download NAV data for multiple schemes, save individual CSVs,
    and create a combined all_live_nav.csv.

    Parameters
    ----------
    schemes : dict[int, str]
        Mapping of AMFI code -> friendly scheme name.

    Returns
    -------
    pd.DataFrame
        Combined NAV data for all schemes.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_frames: list[pd.DataFrame] = []

    for amfi_code, friendly_name in schemes.items():
        logger.info("-" * 50)
        logger.info("Processing: %d - %s", amfi_code, friendly_name)

        data = fetch_nav(amfi_code)
        if data is None:
            logger.warning("Skipping %d due to fetch failure", amfi_code)
            continue

        try:
            meta = data.get("meta", {})
            scheme_name = meta.get("scheme_name", friendly_name)
            scheme_code = meta.get("scheme_code", str(amfi_code))

            records: list[dict] = []
            for entry in data["data"]:
                records.append({
                    "scheme_code": scheme_code,
                    "scheme_name": scheme_name,
                    "date": entry.get("date", ""),
                    "nav": entry.get("nav", ""),
                })

            df = pd.DataFrame(records)

            # Clean NAV values
            df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
            df = df.dropna(subset=["nav"])

            # Parse date (dd-mm-yyyy from API)
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.sort_values("date").reset_index(drop=True)

            # Save individual CSV
            individual_path: Path = RAW_DIR / f"nav_{amfi_code}.csv"
            df.to_csv(individual_path, index=False)
            logger.info(
                "Saved %d rows -> %s", len(df), individual_path.name
            )

            all_frames.append(df)

            print(f"  [OK] {amfi_code} | {scheme_name} | {len(df)} NAV records")

        except Exception as exc:
            logger.error(
                "Failed to process scheme %d: %s", amfi_code, exc
            )

        # Polite delay between API calls
        time.sleep(0.5)

    # Combine all
    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined_path: Path = RAW_DIR / "all_live_nav.csv"
        combined.to_csv(combined_path, index=False)
        logger.info(
            "Combined NAV data: %d total rows -> %s",
            len(combined), combined_path.name,
        )
        return combined

    logger.warning("No NAV data was downloaded")
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """Orchestrate the live NAV fetch pipeline."""
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("BLUESTOCK MF CAPSTONE - LIVE NAV FETCH STARTED")
    logger.info("Timestamp: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 70)

    print("\n" + "=" * 60)
    print("  LIVE NAV DOWNLOAD")
    print("=" * 60)

    combined_df = download_and_export(SCHEMES)

    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 60)
    print(f"  Total NAV records : {len(combined_df)}")
    print(f"  Execution time    : {elapsed:.2f}s")
    print(f"  Output            : {RAW_DIR}")
    print("=" * 60)

    logger.info("=" * 70)
    logger.info("NAV FETCH COMPLETED in %.2f seconds", elapsed)
    logger.info("Total records: %d", len(combined_df))
    logger.info("=" * 70)

    print(f"\n[OK] NAV fetch completed in {elapsed:.2f}s")
    print(f"   Outputs -> {RAW_DIR}")
    print(f"   Logs    -> {LOG_DIR / 'nav_fetch.log'}")


if __name__ == "__main__":
    main()
