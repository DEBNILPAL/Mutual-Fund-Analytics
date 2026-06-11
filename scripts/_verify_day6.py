"""Verify all Day 6 outputs."""
from pathlib import Path

base = Path(r"d:\Downloads\BlueStock Project\project_1")
proc = base / "data" / "processed"
charts_dir = base / "reports" / "charts"

csvs = [
    "var_summary.csv", "cohort_analysis.csv", "investor_segments.csv",
    "fund_recommendations.csv", "monte_carlo_projections.csv",
    "efficient_frontier.csv", "optimal_portfolios.csv",
    "risk_scorecard.csv", "day6_validation_report.csv",
]

charts = [
    "var_distribution.png", "cvar_comparison.png",
    "cohort_retention.png", "cohort_growth.png", "cohort_redemption.png",
    "investor_segments.png",
    "monte_carlo_top_fund.png", "monte_carlo_fan_chart.png",
    "efficient_frontier.png", "portfolio_allocation.png",
    "rolling_sharpe.png", "rolling_volatility.png", "rolling_beta.png",
    "advanced_correlation_heatmap.png", "correlation_network.png",
]

print("=== CSVs ===")
csv_ok = 0
for f in csvs:
    p = proc / f
    if p.exists():
        print(f"  [OK]   {f:40s} {p.stat().st_size:>10,} bytes")
        csv_ok += 1
    else:
        print(f"  [MISS] {f}")

print("\n=== Charts ===")
chart_ok = 0
for c in charts:
    p = charts_dir / c
    if p.exists():
        print(f"  [OK]   {c}")
        chart_ok += 1
    else:
        print(f"  [MISS] {c}")

nb = base / "notebooks" / "05_Advanced_Analytics.ipynb"
rpt = base / "reports" / "advanced_analytics_summary.md"
log = base / "logs" / "advanced_analytics.log"

print(f"\n{'='*50}")
print(f"  CSVs:     {csv_ok}/{len(csvs)}")
print(f"  Charts:   {chart_ok}/{len(charts)}")
print(f"  Notebook: {'OK' if nb.exists() else 'MISS'}")
print(f"  Report:   {'OK' if rpt.exists() else 'MISS'}")
print(f"  Log:      {'OK' if log.exists() else 'MISS'}")
print(f"{'='*50}")
