# Bluestock MF — EDA Summary Report

**Generated:** 2026-06-03 19:45:43  
**Author:** DEBNIL PAL  
**Day:** 3 — Exploratory Data Analysis  

---

## Execution Summary

| Metric | Value |
|--------|-------|
| Total charts generated | 28 |
| Total rows analysed | 88,839 |
| Tables loaded | 11 |
| Key findings | 10 |
| Execution time | 20.6s |

---

## Charts Catalogue

| # | Chart File | Description |
|---|-----------|-------------|
| 1 | `nav_trends_all_funds.png` | Daily NAV trends for all 40 schemes (2022–2026) |
| 2 | `nav_trends_interactive.html` | Interactive NAV trends (Plotly) |
| 3 | `top_funds_nav_growth.png` | Top 5 schemes by NAV growth |
| 4 | `aum_growth_by_amc.png` | AUM growth by fund house (grouped bar) |
| 5 | `sip_inflow_trend.png` | SIP monthly inflow trend with 3M rolling avg |
| 6 | `sip_inflow_trend.html` | Interactive SIP inflow trend (Plotly) |
| 7 | `category_inflow_heatmap.png` | Category-wise net inflow heatmap |
| 8 | `age_group_distribution.png` | Investor age group distribution (pie) |
| 9 | `sip_boxplot_agegroup.png` | SIP amount by age group (box plot) |
| 10 | `gender_distribution.png` | Investor gender distribution |
| 11 | `avg_investment_by_gender.png` | Investment amount by gender |
| 12 | `age_income_analysis.png` | Age vs income scatter analysis |
| 13 | `state_sip_distribution.png` | State-wise SIP amount (horizontal bar) |
| 14 | `t30_b30_distribution.png` | T30 vs B30 city tier distribution |
| 15 | `state_transaction_count.png` | Transaction count by state |
| 16 | `folio_growth.png` | Industry folio growth (2022–2025) |
| 17 | `nav_correlation_matrix.png` | Daily return correlation — top 10 funds |
| 18 | `sector_allocation_donut.png` | Sector allocation (donut chart) |
| 19 | `top_sectors.png` | Top 10 sectors by portfolio weight |
| 20 | `transaction_type_distribution.png` | Transaction type distribution |
| 21 | `monthly_transaction_volume.png` | Monthly transaction volume |
| 22 | `amc_market_share.png` | AMC market share by transaction count |
| 23 | `benchmark_trends.png` | Benchmark index trends (2022–2026) |
| 24 | `benchmark_trends_interactive.html` | Interactive benchmark trends (Plotly) |
| 25 | `risk_category_distribution.png` | Fund distribution by risk category |
| 26 | `expense_ratio_distribution.png` | Expense ratio distribution |
| 27 | `portfolio_diversification.png` | Portfolio diversification score (HHI) |
| 28 | `sharpe_vs_return.png` | Sharpe ratio vs 3-year return scatter |

---

## Top Insights

1. **SBI Mutual Fund dominates industry AUM with the largest asset base among all AMCs.** — ₹12.5 Lakh Crore AUM (latest quarter).
2. **Monthly SIP inflows reached an all-time high, reflecting sustained retail investor confidence.** — ₹31,002 Cr in 2025-12-01.
3. **Industry folio count nearly doubled from 13.26 Cr to 26.12 Cr, indicating massive retail participation growth.** — From 13.26 Cr (Jan 2022) to 26.12 Cr (Dec 2025) — 97% growth in 4 years.
4. **The 26-35 age group dominates mutual fund investments.** — 41.1% of all transactions come from the 26-35 cohort.
5. **T30 (Top 30) cities continue to dominate mutual fund transactions, revealing geographic concentration risk.** — T30 accounts for 66.3% of all transactions vs B30 at 33.7%.

---

## Summary Statistics

| Table | Rows |
|-------|------|
| dim_fund | 40 |
| dim_date | 1,306 |
| fact_nav | 46,000 |
| fact_aum | 90 |
| fact_sip_industry | 48 |
| fact_category_inflows | 144 |
| fact_transactions | 32,778 |
| fact_portfolio | 322 |
| fact_benchmark | 8,050 |
| fact_performance | 40 |
| fact_industry_folios | 21 |

---

*End of EDA Summary Report*
