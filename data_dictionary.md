# Bluestock MF Capstone -- Data Dictionary

**Author:** DEBNIL PAL  
**Date:** 2026-06-02  
**Version:** Day 2

---

## Table of Contents

1. [Raw Datasets](#1-raw-datasets)
2. [Processed Datasets](#2-processed-datasets)
3. [Dimension Tables](#3-dimension-tables)
4. [Fact Tables](#4-fact-tables)

---

## 1. Raw Datasets

### 01_fund_master.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| amfi_code | int | Unique AMFI scheme code | PRIMARY KEY, unique, > 0 | AMFI Registry |
| fund_house | str | Asset Management Company name | NOT NULL | AMFI |
| scheme_name | str | Full scheme name | NOT NULL | AMFI |
| category | str | Broad fund category (Equity/Debt) | IN ('Equity','Debt','Hybrid') | SEBI |
| sub_category | str | Sub-category (Large Cap, Mid Cap, etc.) | NOT NULL | SEBI |
| plan | str | Direct or Regular plan | IN ('Direct','Regular') | AMFI |
| launch_date | date | Scheme launch date | Valid date, <= today | AMFI |
| benchmark | str | Benchmark index name | NOT NULL | Fund House |
| expense_ratio_pct | float | Annual expense ratio (%) | 0.0 - 3.0 | Fund House |
| exit_load_pct | float | Exit load percentage | >= 0 | Fund House |
| min_sip_amount | int | Minimum SIP amount (INR) | > 0 | Fund House |
| min_lumpsum_amount | int | Minimum lumpsum investment (INR) | > 0 | Fund House |
| fund_manager | str | Name of fund manager | NOT NULL | Fund House |
| risk_category | str | Risk classification | IN ('Low','Moderate','Moderately High','High','Very High') | SEBI |
| sebi_category_code | str | SEBI category identifier | NOT NULL | SEBI |

### 02_nav_history.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| amfi_code | int | AMFI scheme code (FK to fund_master) | EXISTS in fund_master | AMFI |
| date | date | NAV date | Valid business date | AMFI |
| nav | float | Net Asset Value per unit (INR) | > 0 | AMFI |

### 03_aum_by_fund_house.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| fund_house | str | AMC name | NOT NULL | AMFI |
| date | date | Reporting date | Valid date | AMFI |
| aum_lakh_crore | float | AUM in lakh crore INR | > 0 | AMFI |
| aum_crore | float | AUM in crore INR | > 0 | AMFI |
| num_schemes | int | Number of schemes under management | > 0 | AMFI |

### 04_monthly_sip_inflows.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| month | str | Reporting month (YYYY-MM) | Valid month format | AMFI |
| sip_inflow_crore | float | Monthly SIP inflow (crore INR) | > 0 | AMFI |
| active_sip_accounts_crore | float | Active SIP accounts (in crores) | > 0 | AMFI |
| new_sip_accounts_lakh | float | New SIP registrations (in lakhs) | > 0 | AMFI |
| sip_aum_lakh_crore | float | SIP AUM (lakh crore INR) | > 0 | AMFI |
| yoy_growth_pct | float | Year-over-year growth (%) | NULL for first 12 months | AMFI |

### 05_category_inflows.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| month | str | Reporting month (YYYY-MM) | Valid month format | AMFI |
| category | str | Fund category name | NOT NULL | AMFI |
| net_inflow_crore | float | Net category inflow (crore INR) | Can be negative (outflow) | AMFI |

### 06_industry_folio_count.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| month | str | Reporting month (YYYY-MM) | Valid month format | AMFI |
| total_folios_crore | float | Total investor folios (crores) | > 0 | AMFI |
| equity_folios_crore | float | Equity scheme folios (crores) | > 0 | AMFI |
| debt_folios_crore | float | Debt scheme folios (crores) | > 0 | AMFI |
| hybrid_folios_crore | float | Hybrid scheme folios (crores) | > 0 | AMFI |
| others_folios_crore | float | Other scheme folios (crores) | > 0 | AMFI |

### 07_scheme_performance.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| amfi_code | int | AMFI scheme code | FK to fund_master | Fund House |
| scheme_name | str | Scheme name | NOT NULL | Fund House |
| fund_house | str | AMC name | NOT NULL | Fund House |
| category | str | Fund category | NOT NULL | SEBI |
| plan | str | Direct/Regular | IN ('Direct','Regular') | Fund House |
| return_1yr_pct | float | 1-year return (%) | Numeric | Fund House |
| return_3yr_pct | float | 3-year CAGR return (%) | Numeric | Fund House |
| return_5yr_pct | float | 5-year CAGR return (%) | Numeric | Fund House |
| benchmark_3yr_pct | float | Benchmark 3-year CAGR (%) | Numeric | Index Provider |
| alpha | float | Jensen's Alpha | Numeric | Calculated |
| beta | float | Market beta (sensitivity) | Typically 0-3 | Calculated |
| sharpe_ratio | float | Risk-adjusted return metric | Typically > 0 | Calculated |
| sortino_ratio | float | Downside risk-adjusted return | Numeric | Calculated |
| std_dev_ann_pct | float | Annualized standard deviation (%) | > 0 | Calculated |
| max_drawdown_pct | float | Maximum peak-to-trough decline (%) | < 0 typically | Calculated |
| aum_crore | float | Scheme AUM (crore INR) | > 0 | Fund House |
| expense_ratio_pct | float | Annual expense ratio (%) | 0.1 - 2.5 | Fund House |
| morningstar_rating | int | Morningstar star rating | 1-5 | Morningstar |
| risk_grade | str | Risk grade classification | NOT NULL | Morningstar |

### 08_investor_transactions.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| investor_id | str | Unique investor identifier | NOT NULL | Platform |
| transaction_date | date | Transaction date | Valid date | Platform |
| amfi_code | int | AMFI scheme code | FK to fund_master | AMFI |
| transaction_type | str | Type of transaction | IN ('SIP','Lumpsum','Redemption') | Platform |
| amount_inr | float | Transaction amount (INR) | > 0 | Platform |
| state | str | Investor state | NOT NULL | KYC |
| city | str | Investor city | NOT NULL | KYC |
| city_tier | str | City classification | IN ('T30','B30') | AMFI |
| age_group | str | Investor age bracket | NOT NULL | KYC |
| gender | str | Investor gender | IN ('Male','Female') | KYC |
| annual_income_lakh | float | Annual income (lakh INR) | > 0 | KYC |
| payment_mode | str | Payment method | NOT NULL | Platform |
| kyc_status | str | KYC verification status | IN ('Verified','Pending') | KYC |

### 09_portfolio_holdings.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| amfi_code | int | AMFI scheme code | FK to fund_master | Fund House |
| stock_symbol | str | NSE/BSE stock ticker | NOT NULL | Exchange |
| stock_name | str | Full company name | NOT NULL | Exchange |
| sector | str | Industry sector | NOT NULL | Exchange |
| weight_pct | float | Portfolio weight (%) | 0-100, sum ~100 per scheme | Fund House |
| market_value_cr | float | Market value (crore INR) | > 0 | Fund House |
| current_price_inr | float | Current stock price (INR) | > 0 | Exchange |
| portfolio_date | date | Holdings reporting date | Valid date | Fund House |

### 10_benchmark_indices.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| date | date | Trading date | Valid business date | NSE |
| index_name | str | Benchmark index name | NOT NULL | NSE |
| close_value | float | Closing index value | > 0 | NSE |

---

## 2. Processed Datasets

### clean_nav_history.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| date | datetime | NAV date (business days filled) | Valid business date | 02_nav_history |
| amfi_code | int | AMFI scheme code | FK to fund_master | 02_nav_history |
| nav | float | Net Asset Value (forward-filled) | > 0 | 02_nav_history |
| daily_return_pct | float | Daily return = (NAV/prev_NAV - 1) * 100 | Numeric | Computed |
| nav_filled_flag | int | 1 if NAV was forward-filled | IN (0, 1) | Computed |
| nav_anomaly_flag | int | 1 if abs(daily_return) > 50% | IN (0, 1) | Computed |

### clean_investor_transactions.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| *All columns from raw* | | *Standardized and validated* | | 08_investor_transactions |
| high_value_tx_flag | int | 1 if amount_inr > 1,000,000 | IN (0, 1) | Computed |
| invalid_kyc_flag | int | 1 if kyc_status != 'Verified' | IN (0, 1) | Computed |

### clean_scheme_performance.csv

| Column | Datatype | Business Definition | Validation Rule | Source |
|--------|----------|---------------------|-----------------|--------|
| *All columns from raw* | | *Validated numeric types* | | 07_scheme_performance |
| flag_negative_sharpe | int | 1 if sharpe_ratio < 0 | IN (0, 1) | Computed |
| flag_high_beta | int | 1 if beta > 3 | IN (0, 1) | Computed |
| flag_extreme_return | int | 1 if any return > 100% | IN (0, 1) | Computed |
| flag_expense_ratio | int | 1 if expense outside 0.1-2.5% | IN (0, 1) | Computed |

---

## 3. Dimension Tables

### dim_fund

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| amfi_code | INTEGER | AMFI scheme identifier | PK | clean_fund_master |
| fund_house | TEXT | AMC name | | clean_fund_master |
| scheme_name | TEXT | Full scheme name | | clean_fund_master |
| category | TEXT | Broad category | | clean_fund_master |
| sub_category | TEXT | Sub-category | | clean_fund_master |
| plan | TEXT | Direct/Regular | | clean_fund_master |
| launch_date | TEXT | Launch date | | clean_fund_master |
| benchmark | TEXT | Benchmark index | | clean_fund_master |
| expense_ratio_pct | REAL | Expense ratio (%) | | clean_fund_master |
| exit_load_pct | REAL | Exit load (%) | | clean_fund_master |
| min_sip_amount | INTEGER | Min SIP (INR) | | clean_fund_master |
| min_lumpsum_amount | INTEGER | Min lumpsum (INR) | | clean_fund_master |
| fund_manager | TEXT | Fund manager name | | clean_fund_master |
| risk_category | TEXT | Risk classification | | clean_fund_master |
| sebi_category_code | TEXT | SEBI code | | clean_fund_master |

### dim_date

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| date_id | TEXT | Date key (YYYY-MM-DD) | PK | Computed |
| date | TEXT | Calendar date | | Computed |
| year | INTEGER | Year | | Computed |
| quarter | INTEGER | Quarter (1-4) | | Computed |
| month | INTEGER | Month number (1-12) | | Computed |
| month_name | TEXT | Month name (January, etc.) | | Computed |
| week | INTEGER | ISO week number | | Computed |
| day | INTEGER | Day of month | | Computed |
| day_of_week | TEXT | Day name (Monday, etc.) | | Computed |
| is_weekend | INTEGER | 1 if Saturday/Sunday | | Computed |

---

## 4. Fact Tables

### fact_nav

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| nav_id | INTEGER | Auto-increment row ID | PK | System |
| amfi_code | INTEGER | Scheme code | FK -> dim_fund | clean_nav_history |
| date_id | TEXT | Date key | FK -> dim_date | clean_nav_history |
| nav | REAL | Net Asset Value | | clean_nav_history |
| daily_return_pct | REAL | Daily return (%) | | clean_nav_history |
| nav_filled_flag | INTEGER | Forward-fill indicator | | clean_nav_history |
| nav_anomaly_flag | INTEGER | Anomaly indicator | | clean_nav_history |

### fact_transactions

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| tx_id | INTEGER | Auto-increment row ID | PK | System |
| investor_id | TEXT | Investor identifier | | clean_investor_transactions |
| amfi_code | INTEGER | Scheme code | FK -> dim_fund | clean_investor_transactions |
| date_id | TEXT | Date key | FK -> dim_date | clean_investor_transactions |
| transaction_type | TEXT | SIP/Lumpsum/Redemption | | clean_investor_transactions |
| amount_inr | REAL | Transaction value (INR) | | clean_investor_transactions |
| state | TEXT | Investor state | | clean_investor_transactions |
| city | TEXT | Investor city | | clean_investor_transactions |
| city_tier | TEXT | T30/B30 | | clean_investor_transactions |
| age_group | TEXT | Age bracket | | clean_investor_transactions |
| gender | TEXT | Male/Female | | clean_investor_transactions |
| annual_income_lakh | REAL | Annual income (lakhs) | | clean_investor_transactions |
| payment_mode | TEXT | Payment method | | clean_investor_transactions |
| kyc_status | TEXT | KYC status | | clean_investor_transactions |
| high_value_tx_flag | INTEGER | High-value indicator | | clean_investor_transactions |

### fact_performance

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| performance_id | INTEGER | Auto-increment row ID | PK | System |
| amfi_code | INTEGER | Scheme code | FK -> dim_fund | clean_scheme_performance |
| scheme_name | TEXT | Scheme name | | clean_scheme_performance |
| fund_house | TEXT | AMC name | | clean_scheme_performance |
| category | TEXT | Fund category | | clean_scheme_performance |
| plan | TEXT | Direct/Regular | | clean_scheme_performance |
| return_1yr_pct | REAL | 1-year return (%) | | clean_scheme_performance |
| return_3yr_pct | REAL | 3-year CAGR (%) | | clean_scheme_performance |
| return_5yr_pct | REAL | 5-year CAGR (%) | | clean_scheme_performance |
| benchmark_3yr_pct | REAL | Benchmark 3Y CAGR (%) | | clean_scheme_performance |
| alpha | REAL | Jensen's Alpha | | clean_scheme_performance |
| beta | REAL | Market Beta | | clean_scheme_performance |
| sharpe_ratio | REAL | Sharpe Ratio | | clean_scheme_performance |
| sortino_ratio | REAL | Sortino Ratio | | clean_scheme_performance |
| std_dev_ann_pct | REAL | Annualized Std Dev (%) | | clean_scheme_performance |
| max_drawdown_pct | REAL | Max Drawdown (%) | | clean_scheme_performance |
| aum_crore | REAL | AUM (crore INR) | | clean_scheme_performance |
| expense_ratio_pct | REAL | Expense Ratio (%) | | clean_scheme_performance |
| morningstar_rating | INTEGER | Star Rating (1-5) | | clean_scheme_performance |
| risk_grade | TEXT | Risk Grade | | clean_scheme_performance |

### fact_aum

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| aum_id | INTEGER | Auto-increment row ID | PK | System |
| fund_house | TEXT | AMC name | | clean_aum_by_fund_house |
| date_id | TEXT | Date key | FK -> dim_date | clean_aum_by_fund_house |
| aum_lakh_crore | REAL | AUM (lakh crore INR) | | clean_aum_by_fund_house |
| aum_crore | REAL | AUM (crore INR) | | clean_aum_by_fund_house |
| num_schemes | INTEGER | Number of schemes | | clean_aum_by_fund_house |

### fact_sip_industry

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| sip_id | INTEGER | Auto-increment row ID | PK | System |
| date_id | TEXT | Date key | FK -> dim_date | clean_monthly_sip_inflows |
| sip_inflow_crore | REAL | Monthly SIP inflow (Cr) | | clean_monthly_sip_inflows |
| active_sip_accounts_crore | REAL | Active SIP accounts (Cr) | | clean_monthly_sip_inflows |
| new_sip_accounts_lakh | REAL | New SIP accounts (Lakhs) | | clean_monthly_sip_inflows |
| sip_aum_lakh_crore | REAL | SIP AUM (Lakh Cr) | | clean_monthly_sip_inflows |
| yoy_growth_pct | REAL | YoY growth (%) | | clean_monthly_sip_inflows |

### fact_category_inflows

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| inflow_id | INTEGER | Auto-increment row ID | PK | System |
| date_id | TEXT | Date key | FK -> dim_date | clean_category_inflows |
| category | TEXT | Fund category | | clean_category_inflows |
| net_inflow_crore | REAL | Net inflow (Cr) | | clean_category_inflows |

### fact_industry_folios

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| folio_id | INTEGER | Auto-increment row ID | PK | System |
| date_id | TEXT | Date key | FK -> dim_date | clean_industry_folio_count |
| total_folios_crore | REAL | Total folios (Cr) | | clean_industry_folio_count |
| equity_folios_crore | REAL | Equity folios (Cr) | | clean_industry_folio_count |
| debt_folios_crore | REAL | Debt folios (Cr) | | clean_industry_folio_count |
| hybrid_folios_crore | REAL | Hybrid folios (Cr) | | clean_industry_folio_count |
| others_folios_crore | REAL | Others folios (Cr) | | clean_industry_folio_count |

### fact_portfolio

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| holding_id | INTEGER | Auto-increment row ID | PK | System |
| amfi_code | INTEGER | Scheme code | FK -> dim_fund | clean_portfolio_holdings |
| stock_symbol | TEXT | Stock ticker | | clean_portfolio_holdings |
| stock_name | TEXT | Company name | | clean_portfolio_holdings |
| sector | TEXT | Industry sector | | clean_portfolio_holdings |
| weight_pct | REAL | Portfolio weight (%) | | clean_portfolio_holdings |
| market_value_cr | REAL | Market value (Cr) | | clean_portfolio_holdings |
| current_price_inr | REAL | Stock price (INR) | | clean_portfolio_holdings |
| holding_date | TEXT | Holdings date | | clean_portfolio_holdings |

### fact_benchmark

| Column | Datatype | Business Definition | PK/FK | Source |
|--------|----------|---------------------|-------|--------|
| benchmark_id | INTEGER | Auto-increment row ID | PK | System |
| date_id | TEXT | Date key | FK -> dim_date | clean_benchmark_indices |
| index_name | TEXT | Benchmark index name | | clean_benchmark_indices |
| close_value | REAL | Closing value | | clean_benchmark_indices |

---

*End of Data Dictionary*
