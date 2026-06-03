-- =====================================================================
-- Bluestock MF Capstone -- Day 2: Analytical SQL Queries
-- =====================================================================
-- Author : DEBNIL PAL
-- Date   : 2026-06-02
-- DB     : data/db/bluestock_mf.db
-- =====================================================================

-- -----------------------------------------------
-- Q1: Top 5 Fund Houses by Latest AUM (in Crore)
-- Shows the most dominant AMCs in the industry
-- -----------------------------------------------
SELECT
    fund_house,
    MAX(aum_crore) AS latest_aum_crore,
    MAX(num_schemes) AS num_schemes
FROM fact_aum
GROUP BY fund_house
ORDER BY latest_aum_crore DESC
LIMIT 5;


-- -----------------------------------------------
-- Q2: Average NAV per Month (across all schemes)
-- Tracks market movement trends monthly
-- -----------------------------------------------
SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(AVG(n.nav), 4) AS avg_nav,
    COUNT(DISTINCT n.amfi_code) AS schemes_tracked
FROM fact_nav n
JOIN dim_date d ON n.date_id = d.date_id
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- -----------------------------------------------
-- Q3: SIP Year-over-Year Growth Trend
-- Measures the acceleration/deceleration of SIP adoption
-- -----------------------------------------------
SELECT
    d.year,
    d.month_name,
    s.sip_inflow_crore,
    s.active_sip_accounts_crore,
    s.yoy_growth_pct
FROM fact_sip_industry s
JOIN dim_date d ON s.date_id = d.date_id
WHERE s.yoy_growth_pct IS NOT NULL
ORDER BY d.year, d.month;


-- -----------------------------------------------
-- Q4: Transaction Volume and Value by State
-- Identifies the most active investor geographies
-- -----------------------------------------------
SELECT
    state,
    COUNT(*) AS total_transactions,
    SUM(amount_inr) AS total_value_inr,
    ROUND(AVG(amount_inr), 2) AS avg_tx_value,
    SUM(CASE WHEN transaction_type = 'SIP' THEN 1 ELSE 0 END) AS sip_count,
    SUM(CASE WHEN transaction_type = 'Lumpsum' THEN 1 ELSE 0 END) AS lumpsum_count,
    SUM(CASE WHEN transaction_type = 'Redemption' THEN 1 ELSE 0 END) AS redemption_count
FROM fact_transactions
GROUP BY state
ORDER BY total_value_inr DESC;


-- -----------------------------------------------
-- Q5: Funds with Low Expense Ratio (< 1%)
-- Cost-efficient funds attractive to value-conscious investors
-- -----------------------------------------------
SELECT
    f.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.category,
    f.expense_ratio_pct,
    f.risk_category
FROM dim_fund f
WHERE f.expense_ratio_pct < 1.0
ORDER BY f.expense_ratio_pct ASC;


-- -----------------------------------------------
-- Q6: Top 10 Funds by Sharpe Ratio
-- Best risk-adjusted returns -- higher Sharpe = better
-- -----------------------------------------------
SELECT
    p.amfi_code,
    p.scheme_name,
    p.fund_house,
    p.category,
    p.sharpe_ratio,
    p.return_3yr_pct,
    p.std_dev_ann_pct,
    p.risk_grade
FROM fact_performance p
ORDER BY p.sharpe_ratio DESC
LIMIT 10;


-- -----------------------------------------------
-- Q7: Top 10 Funds by Alpha (Outperformance)
-- Funds that beat their benchmark the most
-- -----------------------------------------------
SELECT
    p.amfi_code,
    p.scheme_name,
    p.fund_house,
    p.alpha,
    p.benchmark_3yr_pct,
    p.return_3yr_pct,
    p.return_3yr_pct - p.benchmark_3yr_pct AS excess_return
FROM fact_performance p
ORDER BY p.alpha DESC
LIMIT 10;


-- -----------------------------------------------
-- Q8: Largest Maximum Drawdowns
-- Funds with the steepest peak-to-trough declines
-- -----------------------------------------------
SELECT
    p.amfi_code,
    p.scheme_name,
    p.fund_house,
    p.category,
    p.max_drawdown_pct,
    p.std_dev_ann_pct,
    p.risk_grade
FROM fact_performance p
ORDER BY p.max_drawdown_pct ASC
LIMIT 10;


-- -----------------------------------------------
-- Q9: Transaction Distribution by City Tier
-- Compares T30 (top 30 cities) vs B30 (beyond 30)
-- -----------------------------------------------
SELECT
    city_tier,
    COUNT(*) AS total_transactions,
    SUM(amount_inr) AS total_value_inr,
    ROUND(AVG(amount_inr), 2) AS avg_tx_value,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_transactions), 2) AS pct_of_total
FROM fact_transactions
GROUP BY city_tier
ORDER BY total_transactions DESC;


-- -----------------------------------------------
-- Q10: Average SIP Amount by Age Group
-- Demographic analysis of systematic investment patterns
-- -----------------------------------------------
SELECT
    age_group,
    COUNT(*) AS sip_count,
    ROUND(AVG(amount_inr), 2) AS avg_sip_amount,
    ROUND(MIN(amount_inr), 2) AS min_sip,
    ROUND(MAX(amount_inr), 2) AS max_sip,
    SUM(amount_inr) AS total_sip_value
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY age_group
ORDER BY avg_sip_amount DESC;


-- -----------------------------------------------
-- Q11: Monthly NAV Volatility (Std Dev of Daily Returns)
-- Measures market turbulence over time
-- -----------------------------------------------
SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(AVG(n.daily_return_pct), 4) AS avg_daily_return,
    COUNT(*) AS trading_days
FROM fact_nav n
JOIN dim_date d ON n.date_id = d.date_id
WHERE n.daily_return_pct IS NOT NULL
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- -----------------------------------------------
-- Q12: Category Performance Comparison
-- Head-to-head comparison of fund categories
-- -----------------------------------------------
SELECT
    p.category,
    COUNT(*) AS num_funds,
    ROUND(AVG(p.return_1yr_pct), 2) AS avg_1yr_return,
    ROUND(AVG(p.return_3yr_pct), 2) AS avg_3yr_return,
    ROUND(AVG(p.return_5yr_pct), 2) AS avg_5yr_return,
    ROUND(AVG(p.sharpe_ratio), 2) AS avg_sharpe,
    ROUND(AVG(p.alpha), 2) AS avg_alpha,
    ROUND(AVG(p.max_drawdown_pct), 2) AS avg_max_drawdown
FROM fact_performance p
GROUP BY p.category
ORDER BY avg_3yr_return DESC;
