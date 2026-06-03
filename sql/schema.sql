-- =====================================================================
-- Bluestock MF Capstone -- Day 2: SQLite Data Warehouse Schema
-- =====================================================================
-- Author : DEBNIL PAL
-- Date   : 2026-06-02
-- DB     : data/db/bluestock_mf.db
-- =====================================================================

-- -----------------------------------------------
-- DIMENSION: dim_fund
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code           INTEGER PRIMARY KEY,
    fund_house          TEXT NOT NULL,
    scheme_name         TEXT NOT NULL,
    category            TEXT,
    sub_category        TEXT,
    plan                TEXT,
    launch_date         TEXT,
    benchmark           TEXT,
    expense_ratio_pct   REAL,
    exit_load_pct       REAL,
    min_sip_amount      INTEGER,
    min_lumpsum_amount  INTEGER,
    fund_manager        TEXT,
    risk_category       TEXT,
    sebi_category_code  TEXT
);

-- -----------------------------------------------
-- DIMENSION: dim_date
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id         TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    month_name      TEXT NOT NULL,
    week            INTEGER NOT NULL,
    day             INTEGER NOT NULL,
    day_of_week     TEXT NOT NULL,
    is_weekend      INTEGER NOT NULL DEFAULT 0
);

-- -----------------------------------------------
-- FACT: fact_nav
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL,
    date_id             TEXT NOT NULL,
    nav                 REAL NOT NULL,
    daily_return_pct    REAL,
    nav_filled_flag     INTEGER DEFAULT 0,
    nav_anomaly_flag    INTEGER DEFAULT 0,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- FACT: fact_transactions
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_transactions (
    tx_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id         TEXT NOT NULL,
    amfi_code           INTEGER NOT NULL,
    date_id             TEXT NOT NULL,
    transaction_type    TEXT NOT NULL,
    amount_inr          REAL NOT NULL,
    state               TEXT,
    city                TEXT,
    city_tier           TEXT,
    age_group           TEXT,
    gender              TEXT,
    annual_income_lakh  REAL,
    payment_mode        TEXT,
    kyc_status          TEXT,
    high_value_tx_flag  INTEGER DEFAULT 0,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- FACT: fact_performance
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_performance (
    performance_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL,
    scheme_name         TEXT,
    fund_house          TEXT,
    category            TEXT,
    plan                TEXT,
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    benchmark_3yr_pct   REAL,
    alpha               REAL,
    beta                REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    std_dev_ann_pct     REAL,
    max_drawdown_pct    REAL,
    aum_crore           REAL,
    expense_ratio_pct   REAL,
    morningstar_rating  INTEGER,
    risk_grade          TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- -----------------------------------------------
-- FACT: fact_aum
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_house      TEXT NOT NULL,
    date_id         TEXT NOT NULL,
    aum_lakh_crore  REAL,
    aum_crore       REAL,
    num_schemes     INTEGER,
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- FACT: fact_sip_industry
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sip_industry (
    sip_id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id                     TEXT NOT NULL,
    sip_inflow_crore            REAL,
    active_sip_accounts_crore   REAL,
    new_sip_accounts_lakh       REAL,
    sip_aum_lakh_crore          REAL,
    yoy_growth_pct              REAL,
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- FACT: fact_category_inflows
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_category_inflows (
    inflow_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id         TEXT NOT NULL,
    category        TEXT NOT NULL,
    net_inflow_crore REAL,
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- FACT: fact_industry_folios
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_industry_folios (
    folio_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id                 TEXT NOT NULL,
    total_folios_crore      REAL,
    equity_folios_crore     REAL,
    debt_folios_crore       REAL,
    hybrid_folios_crore     REAL,
    others_folios_crore     REAL,
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- FACT: fact_portfolio
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_portfolio (
    holding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code       INTEGER NOT NULL,
    stock_symbol    TEXT NOT NULL,
    stock_name      TEXT,
    sector          TEXT,
    weight_pct      REAL,
    market_value_cr REAL,
    current_price_inr REAL,
    holding_date    TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- -----------------------------------------------
-- FACT: fact_benchmark
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS fact_benchmark (
    benchmark_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id         TEXT NOT NULL,
    index_name      TEXT NOT NULL,
    close_value     REAL,
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

-- -----------------------------------------------
-- INDEXES
-- -----------------------------------------------
CREATE INDEX IF NOT EXISTS idx_nav_amfi ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_nav_date ON fact_nav(date_id);
CREATE INDEX IF NOT EXISTS idx_tx_amfi ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_tx_date ON fact_transactions(date_id);
CREATE INDEX IF NOT EXISTS idx_perf_amfi ON fact_performance(amfi_code);
CREATE INDEX IF NOT EXISTS idx_aum_date ON fact_aum(date_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_amfi ON fact_portfolio(amfi_code);
CREATE INDEX IF NOT EXISTS idx_benchmark_date ON fact_benchmark(date_id);
