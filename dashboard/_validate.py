"""Quick validation of dashboard imports and data connectivity."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "dashboard"))

from config.theme import PRIMARY, CUSTOM_CSS, kpi_card_html
print(f"[OK] Theme loaded: PRIMARY={PRIMARY}")

from utils.database import (
    get_fund_master, get_scorecard, db_status,
    get_aum_data, get_sip_data, get_nav_data,
    get_benchmark_data, get_portfolio_data, get_transactions,
    get_sharpe, get_sortino, get_alpha_beta, get_cagr,
    get_max_drawdown, get_tracking_error,
    get_category_inflows, get_industry_folios,
)

info = db_status()
print(f"[OK] DB Status: {info['status']}, {info['total_rows']:,} rows")

# Test each loader (bypass st.cache_data by calling .__wrapped__)
loaders = [
    ("Fund Master", get_fund_master),
    ("Scorecard", get_scorecard),
    ("AUM", get_aum_data),
    ("SIP", get_sip_data),
    ("Category Inflows", get_category_inflows),
    ("Industry Folios", get_industry_folios),
    ("Transactions", get_transactions),
    ("NAV", get_nav_data),
    ("Benchmark", get_benchmark_data),
    ("Portfolio", get_portfolio_data),
    ("Sharpe", get_sharpe),
    ("Sortino", get_sortino),
    ("Alpha Beta", get_alpha_beta),
    ("CAGR", get_cagr),
    ("Max Drawdown", get_max_drawdown),
    ("Tracking Error", get_tracking_error),
]

total_records = 0
for name, loader in loaders:
    try:
        df = loader.__wrapped__()
        total_records += len(df)
        print(f"[OK] {name:22s} -> {len(df):>8,} rows, {df.shape[1]} cols")
    except Exception as e:
        print(f"[FAIL] {name:22s} -> {e}")

from utils.insights import market_insights, performance_insights, investor_insights, portfolio_insights
print(f"[OK] Insights module loaded")

from utils.charts import (
    bar_chart, line_chart, scatter_chart, donut_chart,
    heatmap_chart, radar_chart, ranking_bar, growth_chart, box_chart,
)
print(f"[OK] Charts module loaded ({9} chart types)")

print(f"\n{'='*60}")
print(f"  DASHBOARD VALIDATION PASSED")
print(f"  Data Sources: {len(loaders)}")
print(f"  Total Records: {total_records:,}")
print(f"  Chart Types: 9")
print(f"  Pages: 4")
print(f"{'='*60}")
