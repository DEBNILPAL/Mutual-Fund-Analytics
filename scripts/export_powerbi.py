"""Export all datasets for Power BI import."""
import importlib
import sys
from pathlib import Path

_DASHBOARD_DIR = str(Path(__file__).resolve().parent.parent / "dashboard")
if _DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, _DASHBOARD_DIR)

# Dynamic import -- avoids IDE "cannot find module" lint on utils.database
_db = importlib.import_module("utils.database")
get_fund_master = _db.get_fund_master
get_scorecard = _db.get_scorecard
get_aum_data = _db.get_aum_data
get_sip_data = _db.get_sip_data
get_nav_data = _db.get_nav_data
get_benchmark_data = _db.get_benchmark_data
get_portfolio_data = _db.get_portfolio_data
get_transactions = _db.get_transactions
get_sharpe = _db.get_sharpe
get_sortino = _db.get_sortino
get_alpha_beta = _db.get_alpha_beta
get_cagr = _db.get_cagr
get_max_drawdown = _db.get_max_drawdown
get_tracking_error = _db.get_tracking_error
get_category_inflows = _db.get_category_inflows
get_industry_folios = _db.get_industry_folios
get_performance_data = _db.get_performance_data

OUT = Path(__file__).resolve().parent.parent / "powerbi" / "powerbi_dataset_exports"
OUT.mkdir(parents=True, exist_ok=True)

exports = [
    ("dim_fund.csv", get_fund_master),
    ("fact_nav_summary.csv", lambda: get_nav_data.__wrapped__().groupby("amfi_code").agg(
        min_date=("date_id", "min"), max_date=("date_id", "max"),
        records=("nav", "count"), latest_nav=("nav", "last")).reset_index()),
    ("fact_aum.csv", get_aum_data),
    ("fact_sip_industry.csv", get_sip_data),
    ("fact_category_inflows.csv", get_category_inflows),
    ("fact_industry_folios.csv", get_industry_folios),
    ("fact_performance.csv", get_performance_data),
    ("fact_portfolio.csv", get_portfolio_data),
    ("fact_benchmark_summary.csv", lambda: get_benchmark_data.__wrapped__().groupby("index_name").agg(
        min_date=("date_id", "min"), max_date=("date_id", "max"),
        records=("close_value", "count"), latest_close=("close_value", "last")).reset_index()),
    ("fund_scorecard.csv", get_scorecard),
    ("sharpe_values.csv", get_sharpe),
    ("sortino_values.csv", get_sortino),
    ("alpha_beta.csv", get_alpha_beta),
    ("cagr_report.csv", get_cagr),
    ("max_drawdown.csv", get_max_drawdown),
    ("tracking_error.csv", get_tracking_error),
    ("transactions_summary.csv", lambda: get_transactions.__wrapped__().groupby(
        ["transaction_type", "state", "city_tier", "age_group", "gender"]
    ).agg(count=("investor_id", "count"), total_amount=("amount_inr", "sum"),
          avg_amount=("amount_inr", "mean")).reset_index()),
]

for filename, loader in exports:
    try:
        df = loader.__wrapped__() if hasattr(loader, "__wrapped__") else loader()
        df.to_csv(OUT / filename, index=False)
        print(f"[OK] {filename:35s} -> {len(df):>8,} rows")
    except Exception as e:
        print(f"[FAIL] {filename:35s} -> {e}")

print(f"\nExported {len(exports)} datasets to {OUT}")
